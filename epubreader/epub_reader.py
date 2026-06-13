#!/usr/bin/env python3
"""Minimal terminal EPUB reader."""

from __future__ import annotations

import argparse
import atexit
import curses
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import time
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import unquote
from xml.etree import ElementTree as ET

try:
    from .epub_glossary import GLOSSARY, clean_definition, load_large_word_list, load_offline_dictionary, root_hints
except ImportError:
    from epub_glossary import GLOSSARY, clean_definition, load_large_word_list, load_offline_dictionary, root_hints


STATE_PATH = Path.home() / ".local" / "state" / "epub_reader_state.json"
BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "div",
    "dl",
    "dt",
    "dd",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tr",
    "td",
    "th",
    "ul",
}
SKIP_TAGS = {"script", "style", "svg", "math", "head", "title", "meta"}
SUPPORTED_EXTENSIONS = {".epub", ".mobi", ".azw3"}
SEARCH_DIRECTORIES = [
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Books",
    Path.home(),
]
RECURSIVE_ROOTS = {Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Books"}
SKIP_DIR_NAMES = {
    ".cache",
    ".cargo",
    ".codex",
    ".config",
    ".git",
    ".gradle",
    ".local",
    ".npm",
    ".rustup",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}
RECENT_LIMIT = 12
PAIR_BODY = 1
PAIR_TITLE = 2
PAIR_DIVIDER = 3
PAIR_FOOTER = 4
PAIR_MODAL = 5
PAIR_SELECTED = 6
PAIR_HINT = 7
PAIR_ACCENT = 8


@dataclass
class Chapter:
    title: str
    source: str
    raw_text: str


@dataclass
class WrappedChapter:
    title: str
    source: str
    lines: List[str]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        merged = "".join(self.parts)
        merged = html.unescape(merged).replace("\xa0", " ")
        merged = re.sub(r"\r\n?", "\n", merged)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in merged.split("\n")]
        collapsed: List[str] = []
        blank = False
        for line in lines:
            if line:
                collapsed.append(line)
                blank = False
            elif not blank:
                collapsed.append("")
                blank = True
        return "\n".join(collapsed).strip()


class NavDocParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_anchor = False
        self.current_href = ""
        self.current_text: List[str] = []
        self.items: List[Tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        attr_map = dict(attrs)
        href = attr_map.get("href", "").strip()
        if href:
            self.in_anchor = True
            self.current_href = href
            self.current_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self.in_anchor:
            return
        text_value = re.sub(r"\s+", " ", "".join(self.current_text)).strip()
        if text_value:
            self.items.append((self.current_href, text_value))
        self.in_anchor = False
        self.current_href = ""
        self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.in_anchor:
            self.current_text.append(data)


class EpubBook:
    def __init__(self, path: Path) -> None:
        self.original_path = path.expanduser().resolve()
        self.path = self.original_path
        self.title = self.path.stem
        self.chapters: List[Chapter] = []
        self._temp_root: Optional[Path] = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")
        if self.path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("Input must be .epub, .mobi, or .azw3")
        if self.path.suffix.lower() != ".epub":
            self.path = self._convert_to_epub(self.path)

        with zipfile.ZipFile(self.path) as zf:
            opf_path = self._find_opf_path(zf)
            manifest, spine, book_title, toc_id = self._parse_opf(zf, opf_path)
            toc_titles = self._parse_toc(zf, opf_path, manifest, toc_id)
            self.title = book_title or self.title

            loaded: List[Chapter] = []
            for item_id in spine:
                entry = manifest.get(item_id)
                if not entry:
                    continue
                href = entry["href"]
                media_type = entry["media_type"]
                if media_type not in {
                    "application/xhtml+xml",
                    "text/html",
                    "application/xml",
                }:
                    continue
                doc_path = self._resolve_path(opf_path, href)
                try:
                    chapter_html = zf.read(doc_path).decode("utf-8", errors="ignore")
                except KeyError:
                    continue
                text = self._html_to_text(chapter_html)
                if not text:
                    continue
                title = toc_titles.get(self._normalize_href(doc_path))
                if not title:
                    title = self._extract_heading(chapter_html) or Path(href).stem.replace("_", " ")
                loaded.append(Chapter(title=title.strip(), source=doc_path, raw_text=text))

            if not loaded:
                raise ValueError("No readable chapters found in EPUB")
            self.chapters = loaded

    def _convert_to_epub(self, input_path: Path) -> Path:
        converter = shutil.which("ebook-convert")
        if not converter:
            raise ValueError(
                "This file format needs Calibre's 'ebook-convert' command, but it is not installed"
            )

        temp_root = Path(tempfile.mkdtemp(prefix="epub_reader_"))
        output_path = temp_root / f"{input_path.stem}.epub"
        cmd = [
            converter,
            str(input_path),
            str(output_path),
            "--enable-heuristics",
            "--chapter",
            "//h:h1|//h:h2|//h:h3",
        ]
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        except OSError as exc:
            raise ValueError(f"Failed to run ebook-convert: {exc}") from exc

        if result.returncode != 0 or not output_path.exists():
            stderr = result.stderr.strip() or result.stdout.strip() or "unknown conversion error"
            raise ValueError(f"Conversion failed: {stderr}")

        self._temp_root = temp_root
        atexit.register(shutil.rmtree, temp_root, ignore_errors=True)
        return output_path

    def _find_opf_path(self, zf: zipfile.ZipFile) -> str:
        try:
            container_xml = zf.read("META-INF/container.xml")
        except KeyError as exc:
            raise ValueError("EPUB is missing META-INF/container.xml") from exc
        root = ET.fromstring(container_xml)
        ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
        rootfile = root.find(".//c:rootfile", ns)
        if rootfile is None:
            raise ValueError("EPUB container does not declare a package document")
        opf_path = rootfile.attrib.get("full-path")
        if not opf_path:
            raise ValueError("EPUB package path is empty")
        return opf_path

    def _parse_opf(
        self, zf: zipfile.ZipFile, opf_path: str
    ) -> Tuple[Dict[str, Dict[str, str]], List[str], str, Optional[str]]:
        try:
            package_xml = zf.read(opf_path)
        except KeyError as exc:
            raise ValueError(f"EPUB package document not found: {opf_path}") from exc

        root = ET.fromstring(package_xml)
        ns = {
            "opf": "http://www.idpf.org/2007/opf",
            "dc": "http://purl.org/dc/elements/1.1/",
        }

        title = ""
        title_node = root.find(".//dc:title", ns)
        if title_node is not None and title_node.text:
            title = title_node.text.strip()

        manifest: Dict[str, Dict[str, str]] = {}
        for item in root.findall(".//opf:manifest/opf:item", ns):
            item_id = item.attrib.get("id")
            href = item.attrib.get("href")
            media_type = item.attrib.get("media-type", "")
            properties = item.attrib.get("properties", "")
            if item_id and href:
                manifest[item_id] = {
                    "href": href,
                    "media_type": media_type,
                    "properties": properties,
                }

        spine_node = root.find(".//opf:spine", ns)
        if spine_node is None:
            raise ValueError("EPUB spine is missing")

        spine = []
        for itemref in spine_node.findall("opf:itemref", ns):
            ref = itemref.attrib.get("idref")
            if ref:
                spine.append(ref)

        return manifest, spine, title, spine_node.attrib.get("toc")

    def _parse_toc(
        self,
        zf: zipfile.ZipFile,
        opf_path: str,
        manifest: Dict[str, Dict[str, str]],
        toc_id: Optional[str],
    ) -> Dict[str, str]:
        toc_map: Dict[str, str] = {}

        if toc_id and toc_id in manifest:
            item = manifest[toc_id]
            doc_path = self._resolve_path(opf_path, item["href"])
            try:
                toc_xml = zf.read(doc_path)
            except KeyError:
                toc_xml = b""
            if toc_xml:
                toc_map.update(self._parse_ncx(toc_xml, doc_path))

        if toc_map:
            return toc_map

        for item in manifest.values():
            if item["media_type"] == "application/x-dtbncx+xml":
                doc_path = self._resolve_path(opf_path, item["href"])
                try:
                    toc_xml = zf.read(doc_path)
                except KeyError:
                    continue
                toc_map.update(self._parse_ncx(toc_xml, doc_path))
                if toc_map:
                    return toc_map

        for item in manifest.values():
            if "nav" not in item.get("properties", "").split():
                continue
            doc_path = self._resolve_path(opf_path, item["href"])
            try:
                nav_doc = zf.read(doc_path).decode("utf-8", errors="ignore")
            except KeyError:
                continue
            toc_map.update(self._parse_nav_doc(nav_doc, doc_path))
            if toc_map:
                return toc_map

        return toc_map

    def _parse_ncx(self, toc_xml: bytes, toc_path: str) -> Dict[str, str]:
        try:
            root = ET.fromstring(toc_xml)
        except ET.ParseError:
            return {}
        ns = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}
        result: Dict[str, str] = {}
        for nav_point in root.findall(".//ncx:navPoint", ns):
            label = nav_point.findtext("ncx:navLabel/ncx:text", default="", namespaces=ns).strip()
            content = nav_point.find("ncx:content", ns)
            src = content.attrib.get("src", "") if content is not None else ""
            if not label or not src:
                continue
            target = self._resolve_path(toc_path, src)
            result[self._normalize_href(target)] = label
        return result

    def _extract_heading(self, chapter_html: str) -> str:
        match = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", chapter_html, flags=re.I | re.S)
        if not match:
            return ""
        inner = re.sub(r"<[^>]+>", " ", match.group(1))
        return re.sub(r"\s+", " ", html.unescape(inner)).strip()

    def _html_to_text(self, chapter_html: str) -> str:
        parser = TextExtractor()
        parser.feed(chapter_html)
        return parser.text()

    def _parse_nav_doc(self, chapter_html: str, nav_path: str) -> Dict[str, str]:
        parser = NavDocParser()
        parser.feed(chapter_html)
        result: Dict[str, str] = {}
        for href, label in parser.items:
            target = self._resolve_path(nav_path, href)
            result[self._normalize_href(target)] = label
        return result

    def _resolve_path(self, base_path: str, relative: str) -> str:
        clean = unquote(relative.split("#", 1)[0])
        parent = Path(base_path).parent
        resolved = (parent / clean).as_posix()
        return str(Path(resolved))

    def _normalize_href(self, href: str) -> str:
        return href.split("#", 1)[0].lstrip("./")


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Dict[str, Dict[str, object]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def save_position(self, book_path: Path, title: str, chapter_idx: int, line_idx: int) -> None:
        state = self.load()
        key = str(book_path)
        state[key] = {
            "chapter_idx": chapter_idx,
            "line_idx": line_idx,
            "title": title,
            "last_opened": int(time.time()),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def get_position(self, book_path: Path) -> Tuple[int, int]:
        state = self.load().get(str(book_path), {})
        if not isinstance(state, dict):
            return 0, 0
        return int(state.get("chapter_idx", 0)), int(state.get("line_idx", 0))

    def recent_books(self, limit: int = RECENT_LIMIT) -> List[Tuple[Path, Dict[str, object]]]:
        rows: List[Tuple[Path, Dict[str, object]]] = []
        for raw_path, data in self.load().items():
            if not isinstance(data, dict):
                continue
            path = Path(raw_path).expanduser()
            if not path.exists():
                continue
            rows.append((path, data))
        rows.sort(key=lambda item: int(item[1].get("last_opened", 0)), reverse=True)
        return rows[:limit]


class ReaderApp:
    def __init__(self, stdscr, book: EpubBook, state: StateStore) -> None:
        self.stdscr = stdscr
        self.book = book
        self.state = state
        self.chapter_idx, self.line_idx = self.state.get_position(book.original_path)
        self.chapter_idx = max(0, min(self.chapter_idx, len(book.chapters) - 1))
        self.line_idx = max(0, self.line_idx)
        self.wrap_width = 0
        self.view_height = 0
        self.wrapped: List[WrappedChapter] = []
        self.chapter_totals: List[int] = []
        self.total_lines = 0
        self.help_visible = False
        self.lookup_cache: Dict[str, Dict[str, str]] = {}
        self.colors_enabled = False

    def run(self) -> None:
        curses.curs_set(0)
        self.stdscr.keypad(True)
        self.init_theme()
        self.rewrap()
        self.state.save_position(self.book.original_path, self.book.title, self.chapter_idx, self.line_idx)

        while True:
            self.render()
            key = self.stdscr.getch()
            if key == curses.KEY_RESIZE:
                self.rewrap()
                continue
            if not self.handle_key(key):
                break
            self.state.save_position(self.book.original_path, self.book.title, self.chapter_idx, self.line_idx)

    def init_theme(self) -> None:
        self.colors_enabled = False
        if not curses.has_colors():
            return
        curses.start_color()
        try:
            curses.use_default_colors()
            curses.init_pair(PAIR_BODY, curses.COLOR_WHITE, -1)
            curses.init_pair(PAIR_TITLE, curses.COLOR_CYAN, -1)
            curses.init_pair(PAIR_DIVIDER, curses.COLOR_BLUE, -1)
            curses.init_pair(PAIR_FOOTER, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(PAIR_MODAL, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(PAIR_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(PAIR_HINT, curses.COLOR_YELLOW, -1)
            curses.init_pair(PAIR_ACCENT, curses.COLOR_GREEN, -1)
            self.colors_enabled = True
        except curses.error:
            self.colors_enabled = False

    def theme(self, pair: int, fallback: int = curses.A_NORMAL) -> int:
        if not self.colors_enabled:
            return fallback
        return curses.color_pair(pair) | fallback

    def rewrap(self) -> None:
        height, width = self.stdscr.getmaxyx()
        self.view_height = max(3, height - 2)
        new_width = self.column_width(width)
        if new_width == self.wrap_width and self.wrapped:
            self.line_idx = self._clamp_line(self.chapter_idx, self.line_idx)
            return

        had_wrapped_lines = bool(self.wrapped)
        progress = self.global_line_position() if had_wrapped_lines else 0
        self.wrap_width = new_width
        wrapped: List[WrappedChapter] = []
        totals: List[int] = []
        for chapter in self.book.chapters:
            wrapped_lines = self._wrap_text(chapter.raw_text, self.wrap_width)
            wrapped.append(WrappedChapter(chapter.title, chapter.source, wrapped_lines))
            totals.append(len(wrapped_lines))
        self.wrapped = wrapped
        self.chapter_totals = totals
        self.total_lines = max(1, sum(totals))
        if had_wrapped_lines:
            self.restore_global_position(progress)
        else:
            self.chapter_idx = max(0, min(self.chapter_idx, len(self.chapter_totals) - 1))
            self.line_idx = self._clamp_line(self.chapter_idx, self.line_idx)

    def _wrap_text(self, text: str, width: int) -> List[str]:
        lines: List[str] = []
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                lines.append("")
                continue
            wrapped = textwrap.wrap(
                paragraph,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
                replace_whitespace=False,
                drop_whitespace=True,
            )
            lines.extend(wrapped or [""])
        if not lines:
            lines = [""]
        return lines

    def _clamp_line(self, chapter_idx: int, line_idx: int) -> int:
        max_start = max(0, self.chapter_totals[chapter_idx] - 1)
        return max(0, min(line_idx, max_start))

    def column_width(self, terminal_width: int) -> int:
        if terminal_width < 50:
            return max(20, terminal_width - 4)
        return max(20, (terminal_width - 7) // 2)

    def page_capacity(self) -> int:
        return self.view_height * 2

    def global_line_position(self) -> int:
        if not self.chapter_totals:
            return 0
        base = sum(self.chapter_totals[: self.chapter_idx])
        return min(base + self.line_idx, self.total_lines - 1)

    def restore_global_position(self, global_line: int) -> None:
        global_line = max(0, global_line)
        remaining = global_line
        for idx, total in enumerate(self.chapter_totals):
            if remaining < total:
                self.chapter_idx = idx
                self.line_idx = min(remaining, max(0, total - 1))
                return
            remaining -= total
        self.chapter_idx = len(self.chapter_totals) - 1
        self.line_idx = max(0, self.chapter_totals[-1] - 1)

    def handle_key(self, key: int) -> bool:
        if self.help_visible and key not in (ord("?"), ord("h"), 27):
            self.help_visible = False

        if key in (ord("q"), 27):
            return False
        if key in (ord("?"), ord("h")):
            self.help_visible = not self.help_visible
            return True
        if key == 9:
            self.open_toc()
            return True
        if key == ord("/"):
            self.lookup_word()
            return True
        if key in (curses.KEY_DOWN, ord("j")):
            self.move_lines(1)
        elif key in (curses.KEY_UP, ord("k")):
            self.move_lines(-1)
        elif key in (curses.KEY_NPAGE, ord(" ")):
            self.move_lines(self.page_capacity())
        elif key in (curses.KEY_PPAGE, ord("b")):
            self.move_lines(-self.page_capacity())
        elif key in (curses.KEY_RIGHT, ord("n"), ord("l")):
            self.next_chapter()
        elif key in (curses.KEY_LEFT, ord("p")):
            self.prev_chapter()
        elif key == ord("g"):
            self.chapter_idx = 0
            self.line_idx = 0
        elif key == ord("G"):
            self.chapter_idx = len(self.wrapped) - 1
            self.line_idx = max(0, self.chapter_totals[self.chapter_idx] - self.page_capacity())
        elif key == ord("0"):
            self.line_idx = 0
        elif key == ord("$"):
            self.line_idx = max(0, self.chapter_totals[self.chapter_idx] - self.page_capacity())
        return True

    def move_lines(self, delta: int) -> None:
        current_total = self.chapter_totals[self.chapter_idx]
        new_line = self.line_idx + delta

        while new_line < 0 and self.chapter_idx > 0:
            self.chapter_idx -= 1
            prev_total = self.chapter_totals[self.chapter_idx]
            new_line += prev_total
            current_total = prev_total

        while new_line >= current_total and self.chapter_idx < len(self.wrapped) - 1:
            new_line -= current_total
            self.chapter_idx += 1
            current_total = self.chapter_totals[self.chapter_idx]

        self.line_idx = max(0, min(new_line, max(0, current_total - 1)))

    def next_chapter(self) -> None:
        if self.chapter_idx < len(self.wrapped) - 1:
            self.chapter_idx += 1
            self.line_idx = 0

    def prev_chapter(self) -> None:
        if self.chapter_idx > 0:
            self.chapter_idx -= 1
            self.line_idx = 0

    def open_toc(self) -> None:
        if not self.wrapped:
            return

        selected = self.chapter_idx
        top = 0
        while True:
            height, width = self.stdscr.getmaxyx()
            box_w = min(max(36, width - 10), width - 2)
            box_h = min(max(8, height - 6), height - 2, len(self.wrapped) + 4)
            visible_rows = max(1, box_h - 4)

            if selected < top:
                top = selected
            elif selected >= top + visible_rows:
                top = selected - visible_rows + 1

            start_y = max(1, (height - box_h) // 2)
            start_x = max(1, (width - box_w) // 2)
            win = curses.newwin(box_h, box_w, start_y, start_x)
            win.keypad(True)
            win.bkgd(" ", self.theme(PAIR_MODAL))
            win.box()
            win.addnstr(
                0,
                2,
                f" Contents  {selected + 1}/{len(self.wrapped)} ",
                box_w - 4,
                self.theme(PAIR_TITLE, curses.A_BOLD),
            )

            for row in range(visible_rows):
                chapter_idx = top + row
                if chapter_idx >= len(self.wrapped):
                    break
                marker = ">" if chapter_idx == self.chapter_idx else " "
                label = f"{marker} {chapter_idx + 1:>3}. {self.wrapped[chapter_idx].title}"
                attr = self.theme(PAIR_SELECTED) if chapter_idx == selected else self.theme(PAIR_MODAL)
                win.addnstr(row + 2, 2, self._pad(label, box_w - 4), box_w - 4, attr)

            hint = "enter open  j/k move  space/b page  esc close"
            win.addnstr(box_h - 2, 2, self._trim(hint, box_w - 4), box_w - 4, self.theme(PAIR_HINT, curses.A_DIM))
            win.refresh()

            key = win.getch()
            if key in (27, ord("q"), 9):
                return
            if key in (10, 13, curses.KEY_ENTER):
                self.chapter_idx = selected
                self.line_idx = 0
                return
            if key in (curses.KEY_DOWN, ord("j")):
                selected = min(len(self.wrapped) - 1, selected + 1)
            elif key in (curses.KEY_UP, ord("k")):
                selected = max(0, selected - 1)
            elif key in (curses.KEY_NPAGE, ord(" ")):
                selected = min(len(self.wrapped) - 1, selected + visible_rows)
            elif key in (curses.KEY_PPAGE, ord("b")):
                selected = max(0, selected - visible_rows)
            elif key in (curses.KEY_HOME, ord("g")):
                selected = 0
            elif key in (curses.KEY_END, ord("G")):
                selected = len(self.wrapped) - 1

    def render(self) -> None:
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()
        chapter = self.wrapped[self.chapter_idx]
        top = self.line_idx

        title = self._trim(f"{self.book.title}  |  {chapter.title}", width - 1)
        self.stdscr.addnstr(0, 0, title, width - 1, self.theme(PAIR_TITLE, curses.A_BOLD))

        if width < 50:
            bottom = min(len(chapter.lines), top + self.view_height)
            for row, line in enumerate(chapter.lines[top:bottom], start=1):
                self.stdscr.addnstr(row, 1, line, max(1, width - 2), self.theme(PAIR_BODY))
        else:
            divider_x = width // 2
            left_x = 1
            right_x = divider_x + 3
            left_width = max(1, divider_x - left_x - 2)
            right_width = max(1, width - right_x - 1)

            for row in range(1, height - 1):
                self.stdscr.addch(row, divider_x, curses.ACS_VLINE, self.theme(PAIR_DIVIDER, curses.A_DIM))

            left_start = top
            right_start = top + self.view_height
            for offset in range(self.view_height):
                row = offset + 1
                left_idx = left_start + offset
                right_idx = right_start + offset
                if left_idx < len(chapter.lines):
                    self.stdscr.addnstr(row, left_x, chapter.lines[left_idx], left_width, self.theme(PAIR_BODY))
                if right_idx < len(chapter.lines):
                    self.stdscr.addnstr(row, right_x, chapter.lines[right_idx], right_width, self.theme(PAIR_BODY))

        footer = self.build_footer(width)
        self.stdscr.addnstr(height - 1, 0, footer, width - 1, self.theme(PAIR_FOOTER, curses.A_REVERSE))

        if self.help_visible:
            self.render_help()

        self.stdscr.refresh()

    def build_footer(self, width: int) -> str:
        chapter = self.wrapped[self.chapter_idx]
        chapter_total = max(1, self.chapter_totals[self.chapter_idx])
        current = min(self.line_idx + 1, chapter_total)
        overall = self.global_line_position() + 1
        percent = int((overall / self.total_lines) * 100)
        remaining = max(0, self.total_lines - overall)
        left = f"{percent:>3}%  {overall}/{self.total_lines} lines  {remaining} left"
        right = f"{self.chapter_idx + 1}/{len(self.wrapped)}  2-col  tab toc  j/k scroll  space/b page  ? help  q quit"
        if len(left) + len(right) + 3 <= width:
            footer = f"{left}   {right}"
        else:
            footer = f"{chapter.title}  {current}/{chapter_total}  {percent}%"
        return self._pad(footer, width - 1)

    def render_help(self) -> None:
        lines = [
            "Navigation",
            "j/k or arrows: scroll line",
            "space / b: page down / up",
            "n / p: next / previous chapter",
            "tab: table of contents",
            "g / G: first / last chapter",
            "0 / $: chapter start / end",
            "/: define a word",
            "? or h: toggle help",
            "q or Esc: quit",
        ]
        height, width = self.stdscr.getmaxyx()
        box_w = min(max(len(line) for line in lines) + 4, width - 4)
        box_h = min(len(lines) + 2, height - 2)
        start_y = max(1, (height - box_h) // 2)
        start_x = max(2, (width - box_w) // 2)
        win = curses.newwin(box_h, box_w, start_y, start_x)
        win.bkgd(" ", self.theme(PAIR_MODAL))
        win.box()
        for idx, line in enumerate(lines[: box_h - 2], start=1):
            attr = self.theme(PAIR_TITLE, curses.A_BOLD) if idx == 1 else self.theme(PAIR_MODAL)
            win.addnstr(idx, 2, line, box_w - 4, attr)
        win.refresh()

    def _trim(self, text_value: str, width: int) -> str:
        return text_value if len(text_value) <= width else text_value[: max(0, width - 3)] + "..."

    def _pad(self, text_value: str, width: int) -> str:
        trimmed = self._trim(text_value, width)
        return trimmed + " " * max(0, width - len(trimmed))

    def lookup_word(self) -> None:
        default_word = self.word_near_screen_center()
        query = self.prompt_input("Define", default=default_word)
        if not query:
            return
        result = self.fast_define(query)
        lines = [f"{query.strip()}:"]
        if result.get("meaning"):
            lines.append(result["meaning"])
        if result.get("pronunciation"):
            lines.append(f"say: {result['pronunciation']}")
        if result.get("synonyms"):
            lines.append(f"near: {result['synonyms']}")
        if result.get("hints"):
            lines.append(f"hints: {result['hints']}")
        context = self.find_context_sentence(query)
        if context:
            lines.extend(["", f"in text: {context}"])
        lines.extend(["", "Press any key"])
        self.show_overlay(lines)

    def prompt_input(self, label: str, default: str = "") -> str:
        height, width = self.stdscr.getmaxyx()
        prompt = f"{label}: "
        query = default
        edited = False
        curses.curs_set(1)
        while True:
            self.stdscr.move(height - 1, 0)
            self.stdscr.clrtoeol()
            display = prompt + query
            self.stdscr.addnstr(
                height - 1,
                0,
                self._pad(display, width - 1),
                width - 1,
                self.theme(PAIR_FOOTER, curses.A_REVERSE),
            )
            self.stdscr.move(height - 1, min(len(display), width - 2))
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key in (27,):
                curses.curs_set(0)
                return ""
            if key in (10, 13, curses.KEY_ENTER):
                curses.curs_set(0)
                return query.strip()
            if key in (curses.KEY_BACKSPACE, 127, 8):
                query = query[:-1]
                edited = True
                continue
            if 32 <= key <= 126:
                if default and query == default and not edited:
                    query = chr(key)
                else:
                    query += chr(key)
                edited = True

    def show_overlay(self, lines: List[str]) -> None:
        height, width = self.stdscr.getmaxyx()
        wrapped_lines: List[str] = []
        content_width = max(20, width - 8)
        for line in lines:
            wrapped_lines.extend(textwrap.wrap(line, width=content_width) or [""])
        box_w = min(max(len(line) for line in wrapped_lines) + 4, max(24, width - 4))
        box_h = min(len(wrapped_lines) + 2, max(4, height - 2))
        start_y = max(1, (height - box_h) // 2)
        start_x = max(2, (width - box_w) // 2)
        win = curses.newwin(box_h, box_w, start_y, start_x)
        win.bkgd(" ", self.theme(PAIR_MODAL))
        win.box()
        for idx, line in enumerate(wrapped_lines[: box_h - 2], start=1):
            if idx == 1:
                attr = self.theme(PAIR_TITLE, curses.A_BOLD)
            elif line.startswith(("say:", "near:", "hints:")):
                attr = self.theme(PAIR_HINT, curses.A_DIM)
            elif line.startswith("in text:"):
                attr = self.theme(PAIR_ACCENT, curses.A_DIM)
            else:
                attr = self.theme(PAIR_MODAL)
            win.addnstr(idx, 2, line, box_w - 4, attr)
        win.refresh()
        win.getch()

    def fast_define(self, word: str) -> Dict[str, str]:
        normalized = self.normalize_word(word)
        if not normalized:
            return {"meaning": "Enter a single word."}
        if normalized in self.lookup_cache:
            return self.lookup_cache[normalized]

        candidates = self.definition_candidates(normalized)
        for candidate in candidates:
            if candidate in GLOSSARY:
                result = dict(GLOSSARY[candidate])
                self.lookup_cache[normalized] = result
                return result

        dictionary = load_offline_dictionary()
        for candidate in candidates:
            definition = dictionary.get(candidate)
            if definition:
                result = {"meaning": clean_definition(definition)}
                hints = root_hints(normalized)
                if hints:
                    result["hints"] = "; ".join(hints)
                self.lookup_cache[normalized] = result
                return result

        hints = root_hints(normalized)
        large_words = load_large_word_list()
        known = any(candidate in large_words for candidate in candidates)
        if known and hints:
            result = {
                "meaning": "Known English word; no short definition installed.",
                "hints": "; ".join(hints),
            }
        elif known:
            result = {"meaning": "Known English word; no short definition installed."}
        elif hints:
            result = {"meaning": "No exact offline meaning found.", "hints": "; ".join(hints)}
        else:
            result = {"meaning": "No offline meaning found."}
        self.lookup_cache[normalized] = result
        return result

    def normalize_word(self, word: str) -> str:
        lowered = word.strip().lower()
        lowered = re.sub(r"^[^a-z]+|[^a-z]+$", "", lowered)
        return lowered

    def definition_candidates(self, word: str) -> List[str]:
        candidates = [word]
        if word.endswith("'s"):
            candidates.append(word[:-2])
        if word.endswith("ies") and len(word) > 3:
            candidates.append(word[:-3] + "y")
        if word.endswith("es") and len(word) > 2:
            candidates.append(word[:-2])
        if word.endswith("s") and len(word) > 1:
            candidates.append(word[:-1])
        if word.endswith("ing") and len(word) > 4:
            stem = word[:-3]
            candidates.extend([stem, stem + "e"])
        if word.endswith("ed") and len(word) > 3:
            stem = word[:-2]
            candidates.extend([stem, stem + "e"])
        if word.endswith("ly") and len(word) > 3:
            candidates.append(word[:-2])
        if word.endswith("er") and len(word) > 3:
            candidates.append(word[:-2])
        if word.endswith("est") and len(word) > 4:
            candidates.append(word[:-3])

        deduped: List[str] = []
        seen = set()
        for candidate in candidates:
            if candidate and candidate not in seen:
                deduped.append(candidate)
                seen.add(candidate)
        return deduped

    def find_context_sentence(self, word: str) -> str:
        normalized = self.normalize_word(word)
        if not normalized or not self.wrapped:
            return ""
        chapter = self.wrapped[self.chapter_idx]
        start = max(0, self.line_idx - 2)
        end = min(len(chapter.lines), self.line_idx + self.page_capacity() + 2)
        visible_text = " ".join(line.strip() for line in chapter.lines[start:end] if line.strip())
        if not visible_text:
            return ""

        sentences = re.split(r"(?<=[.!?])\s+", visible_text)
        pattern = re.compile(rf"\b{re.escape(normalized)}\b", re.I)
        for sentence in sentences:
            if pattern.search(sentence):
                return self._trim(re.sub(r"\s+", " ", sentence.strip()), 120)

        expanded_end = min(len(chapter.lines), self.line_idx + (self.page_capacity() * 2))
        nearby_text = " ".join(line.strip() for line in chapter.lines[start:expanded_end] if line.strip())
        sentences = re.split(r"(?<=[.!?])\s+", nearby_text)
        for sentence in sentences:
            if pattern.search(sentence):
                return self._trim(re.sub(r"\s+", " ", sentence.strip()), 120)
        return ""

    def word_near_screen_center(self) -> str:
        if not self.wrapped:
            return ""
        chapter = self.wrapped[self.chapter_idx]
        center = min(len(chapter.lines) - 1, self.line_idx + max(0, self.page_capacity() // 2))
        search_order = [center]
        for offset in range(1, min(6, len(chapter.lines))):
            if center - offset >= 0:
                search_order.append(center - offset)
            if center + offset < len(chapter.lines):
                search_order.append(center + offset)

        for line_idx in search_order:
            words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", chapter.lines[line_idx])
            meaningful = [
                word
                for word in words
                if self.normalize_word(word)
                and self.normalize_word(word) not in {"and", "the", "that", "with", "from", "this", "was", "were", "his", "her"}
            ]
            if meaningful:
                return self.normalize_word(meaningful[len(meaningful) // 2])
        return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read an EPUB file directly in the terminal.")
    parser.add_argument("book", nargs="*", help="Path or partial filename of the book")
    parser.add_argument(
        "--complete",
        metavar="QUERY",
        help="Print completion candidates for the current query",
    )
    return parser.parse_args()


def supported_book_files(search_root: Path, recursive: bool) -> List[Path]:
    found: List[Path] = []
    if not search_root.exists() or not search_root.is_dir():
        return found
    if not recursive:
        try:
            for entry in search_root.iterdir():
                if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                    found.append(entry.resolve())
        except PermissionError:
            return found
        return found

    for current_root, dirs, files in os.walk(search_root):
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in SKIP_DIR_NAMES and not directory.startswith(".")
        ]
        for filename in files:
            path = Path(current_root) / filename
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                found.append(path.resolve())
    return found


def discover_books() -> List[Path]:
    books: List[Path] = []
    seen = set()
    for base in SEARCH_DIRECTORIES:
        recursive = base in RECURSIVE_ROOTS
        for book_path in supported_book_files(base, recursive=recursive):
            raw = str(book_path)
            if raw in seen:
                continue
            seen.add(raw)
            books.append(book_path)
    books.sort(key=lambda path: path.name.lower())
    return books


def resolve_book(query_parts: Sequence[str], books: Optional[Sequence[Path]] = None) -> Path:
    raw_query = " ".join(query_parts).strip()
    candidate = Path(raw_query).expanduser()

    if candidate.exists() and candidate.is_file():
        return candidate.resolve()

    if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
        for base in SEARCH_DIRECTORIES:
            direct = (base / candidate.name).expanduser()
            if direct.exists() and direct.is_file():
                return direct.resolve()

    normalized_query = re.sub(r"\s+", " ", candidate.stem if candidate.suffix else raw_query).strip().lower()
    all_books = list(books) if books is not None else discover_books()
    exact_matches = [path for path in all_books if path.stem.lower() == normalized_query]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        preview = ", ".join(path.name for path in exact_matches[:5])
        raise ValueError(f"Multiple books match '{raw_query}': {preview}")

    partial_matches = [path for path in all_books if normalized_query in path.stem.lower()]
    if len(partial_matches) == 1:
        return partial_matches[0]

    if not partial_matches:
        raise FileNotFoundError(
            f"No book found for '{raw_query}'. Checked: {', '.join(str(path) for path in SEARCH_DIRECTORIES)}"
        )

    preview = ", ".join(path.name for path in partial_matches[:5])
    if len(partial_matches) > 5:
        preview += ", ..."
    raise ValueError(f"Multiple books match '{raw_query}': {preview}")


def print_recent_books(state: StateStore) -> int:
    recent = state.recent_books()
    print("Recent books")
    print("------------")
    if not recent:
        print("No recent books yet.")
        print("Use: epub <filename>")
        return 0

    for index, (path, data) in enumerate(recent, start=1):
        title = str(data.get("title") or path.stem)
        timestamp = int(data.get("last_opened", 0))
        opened = time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp)) if timestamp else "unknown"
        print(f"{index:>2}. {title}")
        print(f"    {path}")
        print(f"    last opened: {opened}")

    print("")
    print("Use: epub <filename>")
    return 0


def print_completion_candidates(query: str) -> int:
    query = query.strip().lower()
    books = discover_books()
    emitted = set()
    for book_path in books:
        options = [book_path.stem, book_path.name]
        for option in options:
            option_key = option.lower()
            if query and query not in option_key:
                continue
            if option in emitted:
                continue
            emitted.add(option)
            print(option)
    return 0


def main() -> int:
    args = parse_args()
    state = StateStore(STATE_PATH)

    if args.complete is not None:
        return print_completion_candidates(args.complete)

    if not args.book:
        return print_recent_books(state)

    try:
        books = discover_books()
        book = EpubBook(resolve_book(args.book, books=books))
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    def runner(stdscr) -> None:
        app = ReaderApp(stdscr, book, state)
        app.run()

    try:
        curses.wrapper(runner)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
