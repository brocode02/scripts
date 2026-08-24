#!/usr/bin/env python3

import subprocess
import sys
import threading
import time

from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

changed = False
changed_caelestia = False


def log(msg):
    print(f"[dotsync] {msg}", file=sys.stderr, flush=True)


class MyeventHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in ("opened", "closed_no_write", "closed"):
            return
        global changed, changed_caelestia
        if "/caelestia/" in event.src_path:
            changed_caelestia = True
            return
            # subprocess.run(
            #     [
            # "rsync",
            # "-a",
            # "--exclude-.git",
            # "--exclude=*~",
            # "--exclude=*.swp",
            # "--exclude=*.swo",
            # "/home/aman/.config/caelestia/",
            # "/home/aman/dotfiles/hyprland/",
            #     ],
            #     capture_output=True,
            #     check=False,
            # )
        elif "/nvim/" in event.src_path:
            subprocess.run(
                [
                    "rsync",
                    "-a",
                    "--exclude=.git",
                    "--exclude=*~",
                    "--exclude=*.swp",
                    "--exclude=*.swo",
                    "/home/aman/.config/nvim/",
                    "/home/aman/dotfiles/lazyvim",
                ],
                capture_output=True,
                check=False,
            )
        elif "/nvchad/lua" in event.src_path:
            subprocess.run(
                [
                    "rsync",
                    "-a",
                    "--exclude=.git",
                    "--exclude=*~",
                    "--exclude=*.swp",
                    "--exclude=*.swo",
                    "/home/aman/.config/nvchad/lua/",
                    "/home/aman/dotfiles/nvchad/lua/",
                ],
                capture_output=True,
                check=False,
            )
        changed = True


def git_sync():
    global changed
    while True:
        time.sleep(60)
        if not changed:
            continue

        log("Syncing dotfiles...")

        subprocess.run(
            ["git", "add", "."],
            cwd="/home/aman/dotfiles/nvchad/",
            capture_output=True,
            check=False,
        )

        commit = subprocess.run(
            ["git", "commit", "-m", "auto backup"],
            cwd="/home/aman/dotfiles/nvchad/",
            capture_output=True,
            text=True,
            check=False,
        )

        if commit.returncode == 0:
            log(f"Committed: {commit.stdout.strip()}")
            result = subprocess.run(
                ["git", "push"],
                cwd="/home/aman/dotfiles/nvchad/",
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                log("Push succeeded")
                subprocess.run(
                    ["notify-send", "Dotfiles", "Synced Sucessfully"], check=False
                )

                changed = False
            else:
                err = result.stderr.strip()[:200]
                log(f"Push failed: {err}")
                subprocess.run(
                    [
                        "notify-send",
                        "-u",
                        "critical",
                        "Dotfiles",
                        f"Push failed: {err}",
                    ],
                    check=False,
                )
        else:
            err = commit.stderr.strip() if commit.stderr else ""
            log(f"Commit: {err}")

            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd="/home/aman/dotfiles/nvchad/",
                capture_output=True,
                text=True,
                check=False,
            )
            if status.stdout.strip() == "":
                changed = False


def git_sync_caelestia():
    global changed_caelestia
    while True:
        time.sleep(60)
        if not changed_caelestia:
            continue

        log("Syncing caelestia...")

        subprocess.run(
            ["git", "add", "."],
            cwd="/home/aman/.config/caelestia/",
            capture_output=True,
            check=False,
        )

        commit = subprocess.run(
            ["git", "commit", "-m", "auto backup"],
            cwd="/home/aman/.config/caelestia/",
            capture_output=True,
            text=True,
            check=False,
        )

        if commit.returncode == 0:
            log(f"Committed (caelestia): {commit.stdout.strip()}")
            result = subprocess.run(
                ["git", "push"],
                cwd="/home/aman/.config/caelestia/",
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                log("Push succeeded (caelestia)")
                subprocess.run(
                    ["notify-send", "Caelestia", "Synced Successfully"], check=False
                )
                changed_caelestia = False
            else:
                err = result.stderr.strip()[:200]
                log(f"Push failed (caelestia): {err}")
                subprocess.run(
                    [
                        "notify-send",
                        "-u",
                        "critical",
                        "Caelestia",
                        f"Push failed: {err}",
                    ],
                    check=False,
                )
        else:
            err = commit.stderr.strip() if commit.stderr else ""
            log(f"Commit (caelestia): {err}")
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd="/home/aman/.config/caelestia/",
                capture_output=True,
                text=True,
                check=False,
            )
            if status.stdout.strip() == "":
                changed_caelestia = False


event_handler = MyeventHandler()
observer = Observer()

# observer.schedule(event_handler, "/home/aman/.config/hypr/", recursive=True)
# observer.schedule(event_handler, "/home/aman/.config/nvim/", recursive=True)
observer.schedule(event_handler, "/home/aman/.config/caelestia/", recursive=True)
observer.schedule(event_handler, "/home/aman/.config/nvchad/lua/", recursive=True)


log("Starting dotfile sync observer")
observer.start()
threading.Thread(target=git_sync, daemon=True).start()
threading.Thread(target=git_sync_caelestia, daemon=True).start()

try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
