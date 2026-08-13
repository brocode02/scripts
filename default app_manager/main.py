import logging
import os
import subprocess
import sys

from categories import MIME_CATEGORIES
from classes import App
from cli import choose_apps, confirmation, display
from defaults import (
    confirm_app,
    default_app,
    get_current_default,
    set_apps,
    supported_apps,
)
from scanner import scanner

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# MIME_CATEGORIES = MIME_CATEGORIES


def clear():
    subprocess.run(["cls" if os.name == "nt" else "clear"], shell=True, check=False)


def main():
    applications = scanner()
    apps = [App(a) for a in applications]
    clear()

    ask_user, options = display(MIME_CATEGORIES)
    app_type = options[ask_user - 1]
    selected_category = MIME_CATEGORIES[app_type]

    matches = supported_apps(apps, selected_category)

    current_default = get_current_default(apps, selected_category)
    clear()
    name, desktop_id = choose_apps(matches, current_default, app_type)

    set_apps(desktop_id, selected_category)
    result_app = default_app(selected_category)
    output = confirm_app(desktop_id, result_app, selected_category)

    confirmation(output, name)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(130)
