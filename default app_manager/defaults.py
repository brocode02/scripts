import subprocess


def supported_apps(applications, selected_category):

    matches = []
    for app in applications:
        if any(MimeType in app["mime"] for MimeType in selected_category):
            matches.append(app)
    return matches


def set_apps(desktop_id, selected_category):
    while True:
        confirm = input("proceed? [y/n]: ")

        if confirm == "y":
            for app_functions in selected_category:
                subprocess.run(
                    [
                        "xdg-mime",
                        "default",
                        desktop_id,
                        app_functions,
                    ]
                )
            break
        elif confirm == "n":
            break
        else:
            print("type a valid response")


def get_current_default(applications, selected_category):
    result = subprocess.run(
        [
            "xdg-mime",
            "query",
            "default",
            selected_category[0],
        ],
        capture_output=True,
        text=True,
    )

    current_desktop = result.stdout.strip()

    for app in applications:
        if app["desktop_id"] == current_desktop:
            return app["name"]

    return current_desktop


def default_app(selected_category):
    results = []
    for app_functions in selected_category:
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
        results.append(result_app.stdout.strip())
    return results


def confirm_app(desktop_id, results):
    return [result == desktop_id for result in results]
