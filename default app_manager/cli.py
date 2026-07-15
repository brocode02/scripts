def display(MIME_CATEGORIES):
    print(
        "===========================\n Linux Default App Manager \n ============================\n"
    )

    options = []
    for i, key in enumerate(MIME_CATEGORIES, start=1):
        print(f"{i}.  {key}")
        options.append(key)
    while True:
        ask_user = input("\nChoose: ")
        if not ask_user.isdigit():
            print(f"Type a no. between 1-{i}")
        ask_user = int(ask_user)
        if ask_user in range(1, i + 1):
            return ask_user, options
        print(f"Type a no between 1-{i}")


def choose_apps(matches, current_default, app_type) -> tuple[str, str]:
    if not matches:
        raise ValueError("No apps found for the selected category.")

    print(f"Current {app_type}\n{current_default}\n===================")
    filtered = [app for app in matches if app.name != current_default]

    for i, matched_app in enumerate(filtered, start=1):
        print(f"{i}: {matched_app.name}")

    while True:
        user_answer = input("Choose app ")
        if not user_answer.isdigit():
            print("Type a number")
            continue
        user_answer = int(user_answer)
        if user_answer in range(1, len(filtered) + 1):
            selected_app = filtered[user_answer - 1]
            return selected_app.name, selected_app.desktop_id
        print(f"Type valid number between 1-{len(filtered)}")


def confirmation(output, name):
    for key, value in output.items():
        if value == "True":
            print(f"{key} set to {name}")
        else:
            print(f"{key} was not set to {name}")
