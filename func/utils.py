"""
Utility functions for file handling, including permission checks, file moving,
logging, and corruption checking.
"""

import os
import csv
import shutil
import sys
import re

def check_folder_permissions(folder_path):
    """
    Ensure that the specified folder exists and has the appropriate write permissions.
    If the folder does not exist, it will be created. If it exists but is not a directory,
    or if it lacks write permissions, an exception will be raised.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    if not os.path.isdir(folder_path):
        raise PermissionError(f"{folder_path} is not a directory.")
    if not os.access(folder_path, os.W_OK):
        raise PermissionError(f"Permission denied: {folder_path}")

def sanitize_filename(filename):
    """
    Remove or replace characters in the filename that are not allowed in file names
    on most operating systems, such as <, >, :, ", /, \, |, ?, *, etc.
    This function also removes any non-alphanumeric characters, except for dots,
    hyphens, and underscores.
    """
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized_name = re.sub(r'[^\w\s.-]', '', sanitized_name)
    return sanitized_name.strip()

def load_downloaded_files(check_file):
    """
    Load the list of previously downloaded files from a text file.
    Each line in the file represents a file that has been downloaded.
    If the file doesn't exist, return an empty set.
    """
    if os.path.exists(check_file):
        with open(check_file, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f)
    return set()

def save_downloaded_file(check_file, file_name):
    """Append the name of a newly downloaded file to the list of downloaded files."""
    with open(check_file, 'a', encoding='utf-8') as f:
        f.write(file_name + '\n')

def move_file(src, dest, messages):
    """
    Move a file from the source path to the destination path.
    If the move is successful, return True. If an error occurs during the move,
    print an error message and return False.
    """
    try:
        shutil.move(src, dest)
        print(messages['video_saved_and_moved'].format(dest))
        return True
    except (shutil.Error, OSError):
        print(messages['error_move_file'].format(os.path.basename(src)))
        return False

def remove_file_info(file_path, file_name):
    """
    Remove a specific file's information from a CSV log file.
    The log file is read line by line, and any lines that do not match the
    specified file_name are rewritten to the file.
    """
    lines = []

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            lines = list(reader)

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in lines:
            if row[0] != file_name:
                writer.writerow(row)

def update_file_info(file_path, file_name, status, file_size):
    """
    Update or add information about a file in a CSV log file.
    If the file_name exists in the log, its status and size will be updated.
    If the file_name does not exist, a new entry will be created.
    """
    lines = []
    file_exists = False

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            lines = list(reader)

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in lines:
            if row[0] == file_name:
                writer.writerow([file_name, file_size, status])
                file_exists = True
            else:
                writer.writerow(row)

        if not file_exists:
            writer.writerow([file_name, file_size, status])

def get_file_size_from_log(file_info_path, file_name):
    """
    Read the file size of a specific file from a CSV log file.
    The log file is searched for an entry matching the file_name,
    and the file size is returned if found. If the file is not found,
    return None.
    """
    if os.path.exists(file_info_path):
        with open(file_info_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] == file_name:
                    return int(row[1])
    return None

def is_file_corrupted(file_path, file_info_path):
    """
    Check if a file is corrupted by comparing its actual size with the size
    recorded in the log file. If the actual size is smaller than the recorded size,
    the file is considered corrupted. If the file doesn't exist or if there's no log entry,
    it's also considered corrupted.
    """
    if os.path.exists(file_path):
        file_name = os.path.basename(file_path)
        logged_size = get_file_size_from_log(file_info_path, file_name)
        if logged_size is not None:
            actual_size = os.path.getsize(file_path)
            if actual_size >= logged_size:
                return False
        return True
    return False

def acquire_lock(lock_file, messages):
    """
    Acquire a lock to prevent multiple instances of the script from running simultaneously.
    If the lock file already exists, print a message and exit the script.
    """
    if os.path.exists(lock_file):
        print(messages['script_running'])
        sys.exit()
    with open(lock_file, 'w') as f:
        pass

def release_lock(lock_file):
    """
    Release the lock by deleting the lock file.
    This allows other instances of the script to run.
    """
    if os.path.exists(lock_file):
        os.remove(lock_file)
