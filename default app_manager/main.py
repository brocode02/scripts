from cli import choose_apps, display
from scanner import scanner
from defaults import supported_apps, set_apps
from categories import MIME_CATEGORIES

MIME_CATEGORIES = MIME_CATEGORIES


Application = scanner()


ask_user, options = display(MIME_CATEGORIES)

matches = supported_apps(options, ask_user, Application, MIME_CATEGORIES)

name, desktop_id = choose_apps(matches)

set_apps(options, ask_user, name, desktop_id, MIME_CATEGORIES)
