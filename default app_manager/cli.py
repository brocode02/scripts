def display(MIME_CATEGORIES):
    options = []
    for i, key in enumerate(MIME_CATEGORIES, start=1):
        print(f"{i}.  {key}")
        options.append(key)
    ask_user = int(input("\nChoose: "))
    return ask_user, options


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


def confirmation(results, name):
    if all(results):
        print(f"App sucessfully changed to {name} ")
    else:
        print(f"Some mime types were not changed to {name}")
