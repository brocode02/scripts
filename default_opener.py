import subprocess
import os


def available_browser():
    browser = subprocess.run(
        r'grep -l "x-scheme-handler/http\|WebBrowser" /usr/share/applications/*.desktop ~/. local/share/applications/*.desktop / 2>/dev/null',
        capture_output=True,
        text=True,
        shell=True,
    )
    if not browser.stdout.strip():
        print("No browser found")
        return
    return browser.stdout.splitlines()


def choose_browser(browser):
    S_no = 0

    browser_list = []

    for line in browser:
        S_no += 1
        print(f"{S_no}: {os.path.basename(line)}")
        browser_list.append(os.path.basename((line)))

    user_answer = int(input("Choose_browser "))
    return user_answer, browser_list, S_no


def set_browser(user_answer, browser_list, S_no):

    if user_answer in range(1, S_no + 1):
        confirm = input("are you sure? [y/n]").lower()
        if confirm == "y":
            subprocess.run(
                [
                    "xdg-settings",
                    "set",
                    "default-web-browser",
                    browser_list[user_answer - 1],
                ]
            )


def confirm_browser(user_answer, browser_list):
    checked_dict = {}
    user_browser = browser_list[user_answer - 1]
    https = subprocess.run(
        ["xdg-mime", "query", "default", "x-scheme-handler/https"],
        capture_output=True,
        text=True,
    )
    checked_dict["https"] = https.stdout.strip()
    html = subprocess.run(
        ["xdg-mime", "query", "default", "text/html"],
        capture_output=True,
        text=True,
    )
    checked_dict["html"] = html.stdout.strip()
    http = subprocess.run(
        ["xdg-mime", "query", "default", "x-scheme-handler/http"],
        capture_output=True,
        text=True,
    )
    checked_dict["http"] = http.stdout.strip()
    for key, value in checked_dict.items():
        if value == user_browser:
            print(f"your {user_browser} opens {key}")
        else:
            print(f"have error changing {key} link")


browser = available_browser()
user_answer, browser_list, S_no = choose_browser(browser)
set_browser(user_answer, browser_list, S_no)
confirm_browser(user_answer, browser_list)
