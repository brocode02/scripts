#!/usr/bin/env python3


import logging
import os
import pathlib
import shutil
import subprocess

logging.basicConfig()


Help = [
    "ls",
    "pwd",
    "cd",
    "find",
    "open",
    "exit",
    "mkdir",
    "del",
    "ddir",
    "cp",
    "mv",
    "unzip",
]

file_index = {}


def build_index():
    print("Scanning files....")
    for folder, subfolder, files in os.walk("/home/aman/"):
        for file in files:
            fullpath = os.path.join(folder, file)
            if file not in file_index:
                file_index[file] = []
            file_index[file].append(fullpath)
    print("Scan completed")


def unzip_files():
    if len(parts) < 3:
        print("Usage: unzip file Destination ")
        return
    path_to_put = find_files_for_other_functions(parts[1])
    subprocess.run(
        f"7z x '{path_to_put}' '-o{parts[2]}'",
        shell=True,
        check=False,
    )


def delete_directory():
    if len(parts) < 2:
        print("Usage: ddir directory ")
        return

    ask_user = input("are you sure y/n").lower()
    if ask_user == "y":
        try:
            shutil.rmtree(parts[1])
        except FileNotFoundError:
            print("Directory not found")
        except PermissionError:
            print("Permission denied")
        except OSError as e:
            print(f"OS error: {e}")


def find_files_for_other_functions(filename):
    S_no = 1
    try:
        list_files = file_index[filename]
    except KeyError:
        print(f"{filename} not found")
        return
    for i in list_files:
        print(f"{S_no}: {i}")
        S_no += 1

    while True:
        try:
            ask_user = int(input("Choose file:"))
        except ValueError:
            print("Please enter a valid number")
            continue

        if ask_user > len(list_files) or ask_user <= 0:
            print("Invalid number, try again")
            continue

        path_to_put = list_files[ask_user - 1]
        return path_to_put


def copy_files():
    if len(parts) < 3:
        print("Usage: cp filename destination")
        return

    destination = parts[2]
    path_to_put = find_files_for_other_functions(parts[1])
    if path_to_put is None:
        return
    try:
        shutil.copy(path_to_put, destination)
        print("file copied succesfully")
    except shutil.SameFileError:
        print("Source and destination represents the same file.")
    except IsADirectoryError:
        print("Destination is a directory.")
    except PermissionError:
        print("Permission denied.")
    except Exception as e:
        print(f"Error occurred while copying file: {e}")


def current_directory():
    print(os.getcwd())


def ls():
    try:
        ls = os.listdir(os.getcwd())
        for i in ls:
            print(i)
    except PermissionError:
        print("Permission denied to list directory")
    except FileNotFoundError:
        print("Current directory no longer exists")


def change_directory():
    if len(parts) < 2:
        print("Usage: cd directory")
        return
    try:
        os.chdir(parts[1])
    except FileNotFoundError:
        print("Directory not found")
    except PermissionError:
        print("Permission denied")
    except NotADirectoryError:
        print("Not a directory")


def find_files():
    S_no = 1
    if parts[0] == "find":
        if len(parts) < 2:
            print("Usage : find filename")
        else:
            filename = parts[1]

            try:
                list_files = file_index[filename]
            except KeyError:
                print("file not found")
                return

            for i in list_files:
                print(f"{S_no}. {i}")
                S_no += 1


def open_files():
    if len(parts) < 2:
        print("Usage: open filename")
        return
    path_to_put = find_files_for_other_functions(parts[1])
    if path_to_put is None:
        return
    try:
        subprocess.run(["xdg-open", path_to_put], check=True)
    except FileNotFoundError:
        print("xdg-open not found")
    except subprocess.CalledProcessError:
        print("Failed to open file")


def create_folders():
    if len(parts) < 2:
        print("Usage: create directory_name")
        return
    try:
        pathlib.Path(parts[1]).mkdir(parents=True)
    except FileExistsError:
        print(f"Directory {parts[1]} already exists")
    except PermissionError:
        print(f"Permission Denied : unable to create {parts[1]}")
    except Exception as e:
        print(f"An error occured: {e}")


def delete_files():
    if len(parts) < 2:
        print("Usage: del filename")
        return
    path_to_put = find_files_for_other_functions(parts[1])
    if path_to_put is None:
        return
    confirm_user = input("are you sure y/n ")
    if confirm_user == "y":
        try:
            os.remove(path_to_put)
        except FileNotFoundError:
            print("File not found")

        except PermissionError:
            print("Permission denied")
        except IsADirectoryError:
            print("Is a directory, use ddir instead")


def move_files():
    if len(parts) < 3:
        print("Usage: mv source destination")
        return
    path_to_put = find_files_for_other_functions(parts[1])
    if path_to_put is None:
        return
    try:
        shutil.move(path_to_put, parts[2])
    except FileNotFoundError:
        print("File not found")
    except PermissionError:
        print("Permission denied")
    except shutil.Error as e:
        print(f"Move error: {e}")


if __name__ == "__main__":
    print("Welcome!!")
    build_index()

    inside_file_manager = True

    while inside_file_manager:
        command = input("> ")
        parts = command.split()
        if not parts:
            continue
        parts[0] = parts[0].lower()
        if command == "exit":
            inside_file_manager = False
        elif command == "help":
            for i in Help:
                print(f"-{i}")

        elif command == "pwd":
            current_directory()
        elif command == "ls":
            ls()
        elif parts[0] == "cd":
            change_directory()
        elif parts[0] == "find":
            find_files()
        elif parts[0] == "open":
            open_files()
        elif parts[0] == "mkdir":
            create_folders()
        elif parts[0] == "del":
            delete_files()
        elif parts[0] == "ddir":
            delete_directory()
        elif parts[0] == "cp":
            copy_files()
        elif parts[0] == "mv":
            move_files()
        elif parts[0] == "unzip":
            unzip_files()
