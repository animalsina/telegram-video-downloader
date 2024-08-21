import os
import csv
import shutil
import sys
import re

def check_folder_permissions(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    if not os.path.isdir(folder_path):
        raise PermissionError(f"{folder_path} is not a directory.")
    if not os.access(folder_path, os.W_OK):
        raise PermissionError(f"Permission denied: {folder_path}")

def sanitize_filename(filename):
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized_name = re.sub(r'[^\w\s.-]', '', sanitized_name)
    return sanitized_name.strip()

def load_downloaded_files(check_file):
    if os.path.exists(check_file):
        with open(check_file, 'r') as f:
            return set(line.strip() for line in f)
    return set()

def save_downloaded_file(check_file, file_name):
    with open(check_file, 'a') as f:
        f.write(file_name + '\n')

def move_file(src, dest, messages):
    try:
        shutil.move(src, dest)
        print(f"Video saved and moved to: {dest}")
        return True
    except Exception as e:
        print(messages['error_move_file'].format(os.path.basename(src)))
        return False

def remove_file_info(file_path, file_name):
    lines = []

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            lines = list(reader)

    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for row in lines:
            if row[0] != file_name:
                writer.writerow(row)


def update_file_info(file_path, file_name, status, file_size):
    lines = []
    file_exists = False

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            lines = list(reader)

    with open(file_path, 'w', newline='') as f:
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
    """Leggi la dimensione del file dal file di log in formato CSV."""
    if os.path.exists(file_info_path):
        with open(file_info_path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] == file_name:
                    return int(row[1])
    return None

def is_file_corrupted(file_path, file_info_path):
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
    if os.path.exists(lock_file):
        print(messages['script_running'])
        sys.exit()
    open(lock_file, 'w').close()

def release_lock(lock_file):
    if os.path.exists(lock_file):
        os.remove(lock_file)
