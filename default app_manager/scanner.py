import itertools
import configparser
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def scanner():
    directories = [
        Path("/usr/share/applications"),
        Path.home() / ".local/share/applications",
    ]

    file_generator = itertools.chain(
        *(folder.rglob("*.desktop") for folder in directories)
    )

    applications = []

    def is_true(value):
        return str(value).lower() == "true"

    for desktop_file in file_generator:
        config = configparser.ConfigParser(interpolation=None)

        try:
            read_files = config.read(desktop_file)
        except OSError as e:
            logger.warning("Cannot read %s: %s", desktop_file, e)
            continue
        except UnicodeDecodeError as e:
            logger.warning("%s has invalid encoding: %s", desktop_file, e)
            continue

        if not read_files:
            logger.warning("Skipping unreadable desktop file: %s", desktop_file)
            continue

        if "Desktop Entry" not in config:
            continue

        try:
            entry = config["Desktop Entry"]

            if (
                is_true(entry.get("Hidden"))
                or is_true(entry.get("NoDisplay"))
                or entry.get("Type", "Application") != "Application"
                or not entry.get("Exec")
            ):
                continue

            app = {
                "name": entry.get("Name", "Unknown"),
                "exec_cmd": entry.get("Exec", ""),
                "icon": entry.get("Icon", ""),
                "mime": entry.get("MimeType", "").split(";"),
                "categories": entry.get("Categories", ""),
                "desktop_id": desktop_file.name,
                "path": str(desktop_file),
            }
            applications.append(app)

        except (configparser.Error, TypeError) as e:
            logger.warning("Error parsing %s: %s", desktop_file, e)
            continue

    applications.sort(key=lambda app: app["name"])
    return applications
