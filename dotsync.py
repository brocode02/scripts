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

state_caelestia = {"changed": False}
state_nvchad = {"changed": False}


def log(msg):
    print(f"[dotsync] {msg}", file=sys.stderr, flush=True)


class MyeventHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in ("opened", "closed_no_write", "closed"):
            return
        if "/caelestia/" in event.src_path:
            state_caelestia["changed"] = True
            return
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
            state_nvchad["changed"] = True


def git_sync(cwd, commit_message, flag_ref):
    while True:
        time.sleep(60)
        if not flag_ref["changed"]:
            continue
        log(f"Syncing {commit_message}...")
        subprocess.run(["git", "add", "."], cwd=cwd, capture_output=True, check=False)
        commit = subprocess.run(
            ["git", "commit", "-m", "auto backup"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if commit.returncode == 0:
            log(f"Committed {commit_message}: {commit.stdout.strip()}")
            result = subprocess.run(
                ["git", "push"], cwd=cwd, capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                log("Push succeeded")
                subprocess.run(
                    ["notify-send", commit_message, "Synced Sucessfully"], check=False
                )
                flag_ref["changed"] = False
            else:
                err = result.stderr.strip()[:200]
                log(f"Push failed: {err}")
                subprocess.run(
                    [
                        "notify-send",
                        "-u",
                        "critical",
                        commit_message,
                        f"Push failed: {err}",
                    ],
                    check=False,
                )
        else:
            err = commit.stderr.strip() if commit.stderr else ""
            log(f"Commit: {err}")
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            if status.stdout.strip() == "":
                flag_ref["changed"] = False


event_handler = MyeventHandler()
observer = Observer()

observer.schedule(event_handler, "/home/aman/.config/caelestia/", recursive=True)
observer.schedule(event_handler, "/home/aman/.config/nvchad/lua/", recursive=True)


log("Starting dotfile sync observer")
observer.start()
threading.Thread(
    target=git_sync,
    args=("/home/aman/.config/caelestia/", "Caelestia", state_caelestia),
    daemon=True,
).start()
threading.Thread(
    target=git_sync,
    args=("/home/aman/dotfiles/nvchad/", "NvChad", state_nvchad),
    daemon=True,
).start()

try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
