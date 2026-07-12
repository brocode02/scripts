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

    Application = []

    for desktop_file in file_generator:
        config = configparser.ConfigParser(interpolation=None)

        try:
            config.read(desktop_file)

            if "Desktop Entry" not in config:
                continue

            entry = config["Desktop Entry"]
            app = {
                "name": entry.get("Name", "Unknown"),
                "exec_cmd": entry.get("Exec", ""),
                "icon": entry.get("Icon", ""),
                "mime": entry.get("MimeType", ""),
                "categories": entry.get("Categories", ""),
                "desktop_id": desktop_file.name,
            }
            Application.append(app)

        except Exception:
            continue
    return Application
