from pathlib import Path
import itertools
import configparser
import subprocess


directories = [
    Path("/usr/share/applications"),
    Path.home() / ".local/share/applications",
]

file_generator = itertools.chain(*(folder.rglob("*.desktop") for folder in directories))

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

ask_user = input("Enter mime type:\n")


def supported_apps(MimeType):
    matches = {}
    for app in Application:
        mime_list = []
        for m in app["mime"].split(";"):
            if m:
                mime_list.append(m)
        if MimeType in mime_list:
            matches[app["name"]] = app["desktop_id"]
    return matches


matches = supported_apps(ask_user)


def choose_apps(matches) -> tuple[str, str]:
    options = list(matches.items())
    for i, (key, _) in enumerate(options, start=1):
        print(f"{i}: {key}")

    while True:
        user_answer = input("Choose app ")
        if not user_answer.isdigit():
            print("Type a number")
            continue
        user_answer = int(user_answer)
        if user_answer in range(1, len(options) + 1):
            name, desktop_id = options[user_answer - 1]
            return name, desktop_id
        print(f"Type valid number between 1-{len(options)}")


name, desktop_id = choose_apps(matches)


def set_apps(name, desktop_id):
    while True:
        confirm = input("Are you sure [y/n]: ")

        if confirm == "y":
            subprocess.run(
                [
                    "xdg-mime",
                    "default",
                    desktop_id,
                    ask_user,
                ]
            )
            confirm_app(name, desktop_id)
            break
        elif confirm == "n":
            break
        else:
            print("type a valid response")


def confirm_app(name, desktop_id):
    result_app = subprocess.run(
        [
            "xdg-mime",
            "query",
            "default",
            ask_user,
        ],
        capture_output=True,
        text=True,
    )
    if desktop_id == result_app.stdout.strip():
        print(f"App sucessfully changed to {name} ")


set_apps(name, desktop_id)
