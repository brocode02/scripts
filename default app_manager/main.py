from cli import choose_apps, display, confirmation
from scanner import scanner
from defaults import confirm_app, supported_apps, set_apps
from categories import MIME_CATEGORIES

MIME_CATEGORIES = MIME_CATEGORIES


applications = scanner()


ask_user, options = display(MIME_CATEGORIES)
selected_category = MIME_CATEGORIES[options[ask_user - 1]]

matches = supported_apps(applications, selected_category)

name, desktop_id = choose_apps(matches)

set_apps(desktop_id, selected_category)
results = confirm_app(desktop_id, selected_category)

confirmation(results, name)
