#!/usr/bin/env python3

import threading
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileSystemEvent,
)

changed = False


class MyeventHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in ("opened", "closed_no_write", "closed"):
            return
        global changed
        if "/hypr/" in event.src_path:
            subprocess.run(
                "cp -r /home/aman/.config/hypr/ /home/aman/dotfiles/hyprland/",
                shell=True,
            )
        elif "/nvim/" in event.src_path:
            subprocess.run(
                "rsync -a --exclude='.git' /home/aman/.config/nvim/ /home/aman/dotfiles/lazyvim",
                shell=True,
            )
        changed = True


def git_sync():
    global changed
    while True:
        time.sleep(60)
        if changed:
            subprocess.run("git add .", shell=True, cwd="/home/aman/dotfiles/")
            commit = subprocess.run(
                'git commit -m "auto backup"',
                shell=True,
                cwd="/home/aman/dotfiles/",
                capture_output=True,
            )
            if commit.returncode == 0:
                result = subprocess.run(
                    "git push", shell=True, cwd="/home/aman/dotfiles/"
                )
                if result.returncode == 0:
                    subprocess.run(
                        "notify-send 'Dotfiles' 'Synced Sucessfully'", shell=True
                    )
                else:
                    subprocess.run(
                        "notify-send -u 'critical' 'Dotfiles' 'Push failed!!'",
                        shell=True,
                    )
            changed = False


event_handler = MyeventHandler()
observer = Observer()

observer.schedule(event_handler, "/home/aman/.config/hypr/", recursive=True)
observer.schedule(event_handler, "/home/aman/.config/nvim/", recursive=True)

observer.start()
threading.Thread(target=git_sync, daemon=True).start()

try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
