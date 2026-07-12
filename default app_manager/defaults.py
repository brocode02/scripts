import subprocess


def supported_apps(options, ask_user, Application, MIME_CATEGORIES):

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


def set_apps(options, ask_user, name, desktop_id, MIME_CATEGORIES):
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
            confirm_app(name, desktop_id, options, ask_user, MIME_CATEGORIES)
            break
        elif confirm == "n":
            break
        else:
            print("type a valid response")


def confirm_app(name, desktop_id, options, ask_user, MIME_CATEGORIES):
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
