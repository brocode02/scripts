import subprocess


def supported_apps(applications, selected_category):

    matches = []
    for app in applications:
        mime_list = []
        for m in app["mime"]:
            if m:
                mime_list.append(m)
        if any(MimeType in mime_list for MimeType in selected_category):
            matches.append(app)
    return matches


def set_apps(desktop_id, selected_category):
    while True:
        confirm = input("Are you sure [y/n]: ")

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
            confirm_app(desktop_id, selected_category)
            break
        elif confirm == "n":
            break
        else:
            print("type a valid response")


def confirm_app(desktop_id, selected_category):
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
        results.append(result_app.stdout.strip() == desktop_id)
    return results
