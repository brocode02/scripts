import subprocess
import os


def available_browser():
    browser = subprocess.run(
        r'grep -l "x-scheme-handler/http\|WebBrowser" /usr/share/applications/*.desktop ~/. local/share/applications/*.desktop 2>/dev/null',
        capture_output=True,
        text=True,
        shell=True,
    )
    return browser


def choose_browser(browser):
    S_no = 0

    browser_list = []

    for line in browser.stdout.strip().splitlines():
        S_no += 1
        print(f"{S_no}: {os.path.basename(line)}")
        browser_list.append(os.path.basename((line)))

    user_answer = int(input("Choose_browser "))
    return user_answer, browser_list, S_no


def set_browser(user_answer, browser_list, S_no):

    if user_answer in range(1, S_no + 1):
        subprocess.run(
            [
                "xdg-settings",
                "set",
                "default-web-browser",
                browser_list[user_answer - 1],
            ]
        )


browser = available_browser()
user_answer, browser_dict, S_no = choose_browser(browser)
set_browser(user_answer, browser_dict, S_no)
