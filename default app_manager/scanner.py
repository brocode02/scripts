from pathlib import Path
import itertools
import configparser


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
            config.read(desktop_file)

            if "Desktop Entry" not in config:
                continue
            entry = config["Desktop Entry"]

            if is_true(
                entry.get("Hidden")
                or entry.get("NoDisplay")
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

        except Exception:
            continue
    applications.sort(key=lambda app: app["name"])
    return applications
