from pathlib import Path
import itertools
import configparser
import subprocess
from categories import MIME_CATEGORIES


print(
    "===========================\n Linux Default App Manager \n ============================\n"
)


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

MIME_CATEGORIES = MIME_CATEGORIES


def display(MIME_CATEGORIES):
    options = []
    for i, key in enumerate(MIME_CATEGORIES, start=1):
        print(f"{i}.  {key}")
        options.append(key)
    ask_user = int(input("\nChoose: "))
    return ask_user, options


ask_user, options = display(MIME_CATEGORIES)


def supported_apps(options, ask_user):
    matches = []
    for app in Application:
        mime_list = []
        for m in app["mime"].split(";"):
            if m:
                mime_list.append(m)
        if any(
            MimeType in mime_list for MimeType in MIME_CATEGORIES[options[ask_user - 1]]
        ):
            matches.append(app)
    return matches


matches = supported_apps(options, ask_user)


def choose_apps(matches) -> tuple[str, str]:
    for i, matched_app in enumerate(matches, start=1):
        print(f"{i}: {matched_app['name']}  {matched_app['desktop_id']}")

    while True:
        user_answer = input("Choose app ")
        if not user_answer.isdigit():
            print("Type a number")
            continue
        user_answer = int(user_answer)
        if user_answer in range(1, len(matches) + 1):
            selcted_app = matches[user_answer - 1]
            name = selcted_app["name"]
            desktop_id = selcted_app["desktop_id"]
            return name, desktop_id
        print(f"Type valid number between 1-{len(matches)}")


name, desktop_id = choose_apps(matches)


def set_apps(name, desktop_id):
    while True:
        confirm = input("Are you sure [y/n]: ")

        if confirm == "y":
            for app_functions in MIME_CATEGORIES[options[ask_user - 1]]:
                subprocess.run(
                    [
                        "xdg-mime",
                        "default",
                        desktop_id,
                        app_functions,
                    ]
                )
            confirm_app(name, desktop_id, options)
            break
        elif confirm == "n":
            break
        else:
            print("type a valid response")


def confirm_app(name, desktop_id, options):
    results = []
    for app_functions in MIME_CATEGORIES[options[ask_user - 1]]:
        result_app = subprocess.run(
            [
                "xdg-mime",
                "query",
                "default",
                app_functions,
            ],
            capture_output=True,
            text=True,
        )
        results.append(result_app.stdout.strip() == desktop_id)
    if all(results):
        print(f"App sucessfully changed to {name} ")
    else:
        print(f"Some mime types were not changed to {name}")


set_apps(name, desktop_id)
