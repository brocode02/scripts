#!/usr/bin/env python3

import sys
import threading
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileSystemEvent,
)

changed = False


def log(msg):
    print(f"[dotsync] {msg}", file=sys.stderr, flush=True)


class MyeventHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in ("opened", "closed_no_write", "closed"):
            return
        global changed
        if "/hypr/" in event.src_path:
            subprocess.run(
                [
                    "rsync",
                    "-a",
                    "--exclude=*~",
                    "--exclude=*.swp",
                    "--exclude=*.swo",
                    "/home/aman/.config/hypr/",
                    "/home/aman/dotfiles/hyprland/",
                ],
                capture_output=True,
            )
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
            cwd="/home/aman/dotfiles/",
            capture_output=True,
        )

        commit = subprocess.run(
            ["git", "commit", "-m", "auto backup"],
            cwd="/home/aman/dotfiles/",
            capture_output=True,
            text=True,
        )

        if commit.returncode == 0:
            log(f"Committed: {commit.stdout.strip()}")
            result = subprocess.run(
                ["git", "push"],
                cwd="/home/aman/dotfiles/",
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                log("Push succeeded")
                subprocess.run(["notify-send", "Dotfiles", "Synced Sucessfully"])
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
                )
        else:
            err = commit.stderr.strip() if commit.stderr else ""
            log(f"Commit: {err}")

            # If truly nothing to do, reset so we don't loop forever
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd="/home/aman/dotfiles/",
                capture_output=True,
                text=True,
            )
            if status.stdout.strip() == "":
                changed = False


event_handler = MyeventHandler()
observer = Observer()

observer.schedule(event_handler, "/home/aman/.config/hypr/", recursive=True)
observer.schedule(event_handler, "/home/aman/.config/nvim/", recursive=True)

log("Starting dotfile sync observer")
observer.start()
threading.Thread(target=git_sync, daemon=True).start()

try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
