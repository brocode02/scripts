#!/usr/bin/env python3

import os
import sys
import time
import signal
import shutil
import logging
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from file_types import FILE_TYPES

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%b %d %H:%M:%S",
)
logger = logging.getLogger("download-sorter")

downloads = Path("/home/aman/Downloads")
running = True


class MyEventHandler(FileSystemEventHandler):
    def on_moved(self, event):
        if event.is_directory:
            return
        self._sort_file(event.dest_path)

    def on_created(self, event):
        if event.is_directory:
            return
        self._sort_file(event.src_path)

    def _sort_file(self, file_path):
        path = Path(file_path)
        if path.parent.name in set(FILE_TYPES.values()):
            return
        extension = path.suffix.lower()
        if not extension:
            return
        folder_to_put = FILE_TYPES.get(extension)
        if folder_to_put is None:
            return
        destination = downloads / folder_to_put
        try:
            shutil.move(str(path), str(destination))
        except shutil.Error as e:
            logger.error("Error moving %s to %s: %s", path, destination, e)


def handle_signal(signum, frame):
    global running
    logger.info("Received signal %s, shutting down...", signum)
    running = False


def main():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    for folder in set(FILE_TYPES.values()):
        (downloads / folder).mkdir(exist_ok=True)

    logger.info("Started watching %s", downloads)

    event_handler = MyEventHandler()
    observer = Observer()
    observer.schedule(event_handler, str(downloads), recursive=True)
    observer.start()
    try:
        while running:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
