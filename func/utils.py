"""
Utility functions for file handling, including permission checks, file moving,
logging, and corruption checking.
"""
import asyncio
import mimetypes
import os
import csv
import pickle
import shutil
import sys
import re

import ffmpeg

from pathlib import Path

from markdown_it import MarkdownIt

from func.command import CommandHandler
from func.messages import get_message
from func.rules import apply_rules

line_for_info_data = 7
line_for_show_last_error = 9

VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpv']

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


def is_video_file(file_name):
    """Check if the file has a video extension."""
    _, ext = os.path.splitext(file_name)
    return ext.lower() in VIDEO_EXTENSIONS


def sanitize_filename(filename):
    """
    Remove or replace characters in the filename that are not allowed in file names
    on most operating systems, such as <, >, :, \", /, \, |, ?, *, etc.
    This function also removes any non-alphanumeric characters, except for dots,
    hyphens, and underscores.
    """
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized_name = re.sub(r'[^\w\s.-]', '', sanitized_name)
    return sanitized_name.strip()

async def move_file(src: Path, dest: Path, cb=None) -> bool:
    """
    Move a file from the source path to the destination path.
    If the move is successful, return True. If an error occurs during the move,
    print an error message and return False.
    """
    msgs = get_message('')
    try:
        dest_file_name = dest.name
        dest_file_name_without_ext = dest.stem

        base_dest_dir = dest.parent

        dest_dir = base_dest_dir / dest_file_name_without_ext
        dest_dir.mkdir(parents=True, exist_ok=True)

        final_dest = dest_dir / dest_file_name

        shutil.move(str(src), str(final_dest))
        print(msgs['video_saved_and_moved'].format(final_dest))
        if cb is not None:
            await cb(src, final_dest, True)
        return True
    except (shutil.Error, OSError):
        print(msgs['error_move_file'].format(os.path.basename(src)))
        if cb is not None:
            await cb(src, None, False)
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


def is_file_corrupted(file_path, total_file_size):
    """
    Check if a file is corrupted by comparing its actual size with the size
    recorded in the log file. If the actual size is smaller than the recorded size,
    the file is considered corrupted. If the file doesn't exist or if there's no log entry,
    it's also considered corrupted.
    """
    if os.path.exists(file_path):
        if total_file_size is not None:
            actual_size = os.path.getsize(file_path)
            if actual_size >= total_file_size:
                return False
        return True
    return False


def check_lock(lock_file):
    if os.path.exists(lock_file):
        print(get_message('script_running'))
        sys.exit()


def acquire_lock(lock_file):
    """
    Acquire a lock to prevent multiple instances of the script from running simultaneously.
    If the lock file already exists, print a message and exit the script.
    """
    with open(lock_file, 'w'):
        pass


def release_lock(lock_file):
    """
    Release the lock by deleting the lock file.
    This allows other instances of the script to run.
    """
    if os.path.exists(lock_file):
        os.remove(lock_file)


async def compress_video_h265(input_file, output_file, crf=28, callback=None) -> bool:
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Existing old file converted removed: {output_file}")
    try:
        process = (
            ffmpeg
            .input(str(input_file))
            .output(str(output_file), vcodec='libx265', crf=crf, preset='slow', tune='zerolatency', progress='pipe')
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )
        while True:
            # Leggi dall'output standard di errore
            output = process.stderr.read(4096).decode('utf-8')
            if output:  # Se c'è output
                lines = output.splitlines()
                last_line = lines[-1]
                match = re.search(r'time=(\d{2}:\d{2}:\d{2}.\d{2})', last_line)
                time_value = None
                if match:
                    time_value = match.group(1)
                if time_value is not None:
                    if callback and callable(callback):
                        await callback(time_value)  # Chiamata al callback qui
                    print(f"Progress: {time_value}")
                else:
                    await asyncio.sleep(0.1)  # Attendere un attimo prima di controllare di nuovo

            if process.poll() is not None:  # Se il processo è terminato
                break

        print(f"Compression H.265 completed! File save {output_file}")
        return True
    except Exception as e:
        print(f"Error during the compression: {str(e)}")
        return False


async def download_complete_action(video):
    from func.config import load_configuration
    config = load_configuration()
    acquire_lock(config.lock_file)

    messages = config.messages
    mime_type, _ = mimetypes.guess_type(video.file_path)
    extension = mimetypes.guess_extension(mime_type) if mime_type else ''
    completed_folder_mask = apply_rules('completed_folder_mask', video.video_name_cleaned)
    completed_folder = config.completed_folder

    if completed_folder_mask:
        completed_folder = completed_folder_mask

    completed_file_path = os.path.join(completed_folder, video.video_name_cleaned + extension)

    file_path_source = Path(str(video.file_path))
    file_path_dest = Path(str(completed_file_path))

    async def compression_message(time_info):
        await add_line_to_text(video.reference_message, str(get_message('trace_compress_action')).format(time_info),
                               line_for_info_data)

    if config.enable_video_compression:
        print(messages['start_compress_file'].format(file_path_source))
        await add_line_to_text(video.reference_message, messages['start_compress_file'].format(file_path_source),
                               line_for_info_data)
        file_path_c = Path(str(video.file_path))
        converted_file_path = file_path_c.with_name(
            file_path_c.stem + "_converted" + file_path_c.suffix)
        if await compress_video_h265(file_path_source, converted_file_path, config.compression_ratio,
                                     compression_message):
            file_path_source.unlink()
            file_path_source = converted_file_path
            print(messages['complete_compress_file'].format(file_path_source))
            await add_line_to_text(video.reference_message, messages['complete_compress_file'].format(file_path_source),
                                   line_for_info_data)
        else:
            print(messages['cant_compress_file'].format(file_path_source))
            await add_line_to_text(video.reference_message, messages['cant_compress_file'].format(file_path_source),
                                   line_for_show_last_error)
            raise

    await add_line_to_text(video.reference_message, messages['ready_to_move'].format(video.video_name_cleaned),
                           line_for_info_data)

    print(messages['ready_to_move'].format(video.video_name_cleaned))

    async def cb_move_file(src, target, result):
        if result:
            complete_pickle_file(video)
            await add_line_to_text(video.reference_message, messages['download_complete'].format(video.video_name_cleaned),
                                   line_for_info_data)
        else:
            await add_line_to_text(video.reference_message, messages['error_move_file'].format(video.video_name_cleaned),
                                   line_for_show_last_error)

    await move_file(file_path_source, file_path_dest, cb_move_file)


def remove_pickle_file(video):
    if os.path.isfile(get_pickle_full_path(video)):
        os.remove(str(get_pickle_full_path(video)))

def pickle_file_exists(video):
    return os.path.exists(get_pickle_full_path(video))

def get_pickle_name(video):
    import run
    return f"{run.client.api_id}_{video.chat_id}_{video.id}.pkl"

def get_pickle_full_path(video):
    return os.path.join(get_pickle_path(), get_pickle_name(video))

def get_pickle_path():
    import run
    return os.path.join(run.root_dir, 'pickles')

def complete_pickle_file(video):
    save_pickle_data({'completed': True}, video, ['completed'])

def load_config(file_path):
    """
    Loads the configuration from the specified path.
    This function reads the configuration file line by line, processes section headers
    (e.g., '[section]'), and key-value pairs (e.g., 'key=value'). It also handles a special case
    for the 'groups' section, storing its values in a separate dictionary.
    """
    config_data = {}
    groups = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        section = None
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue

            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1].strip()  # Section header
            else:
                if '=' in line:  # Key=value pair
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if section == 'groups':
                        # In the 'groups' section, map the value to the key
                        groups[value] = key
                    else:
                        # For other sections, store the key-value pair in config
                        config_data[key] = value

    # Convert min_valid_file_size_mb to bytes, if present
    if 'min_valid_file_size_mb' in config_data:
        try:
            min_size_mb = float(config_data['min_valid_file_size_mb'])
            config_data['min_valid_file_size'] = min_size_mb * 1024 * 1024  # Convert MB to bytes
        except ValueError:
            config_data['min_valid_file_size'] = 0  # Default to 0 if conversion fails
    else:
        config_data['min_valid_file_size'] = 0  # Default to 0 if key is absent

    # Add the 'groups' dictionary to the config under the 'group_chats' key
    config_data['group_chats'] = groups

    return config_data


async def add_line_to_text(reference_message, new_line, line_number):
    # Divide il testo in righe
    lines = reference_message.text.splitlines()

    # Se ci sono meno righe di quelle richieste, aggiunge righe vuote fino alla riga specificata
    while len(lines) < line_number - 1:
        lines.append("")

    # Aggiunge o sostituisce la riga specificata
    if len(lines) >= line_number:
        lines[line_number - 1] = new_line
    else:
        lines.append(new_line)

    # Unisce di nuovo le righe in una singola stringa
    await reference_message.edit("\n".join(lines))


def save_pickle_data(data, video, fields_to_compare=None):
    file_path = get_pickle_full_path(video)

    # Se il file esiste, carica i dati e controlla se ci sono differenze
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            existing_data = pickle.load(f)

        # Confronta i dati esistenti con quelli nuovi; se uguali, termina la funzione
        if fields_to_compare:
            data_subset = {field: getattr(data, field, None) for field in fields_to_compare}
            existing_data_subset = {field: getattr(existing_data, field, None) for field in fields_to_compare}

            # Confronta solo i campi specificati
            if data_subset == existing_data_subset:
                print("Nessuna differenza nei campi selezionati, dati non salvati.")
                return
        else:
            # Confronto di tutto l'oggetto se non sono stati specificati campi
            if data == existing_data:
                print("Nessuna differenza trovata, dati non salvati.")
                return

            for field in vars(data).keys():
                setattr(existing_data, field, getattr(data, field))
            return
    else:
        # Se il file non esiste, usa i nuovi dati
        existing_data = data

    # Salva solo se ci sono differenze
    with open(file_path, "wb") as f:
        pickle.dump(existing_data, f)
    print("Dati salvati con successo.")


def default_video_message(video):
    video_text = "".join(remove_markdown(video.video_name.splitlines()))[:40]
    file_name = "".join(remove_markdown(video.file_name.splitlines()))[:40]
    return (f'🎥 **{video_text}** - {file_name}\n'
            f'⚖️ {format_bytes(video.video_media.document.size)}\n'
            f'↕️ {video.video_attribute.w}x{video.video_attribute.h}\n'
            f'📌 {video.pinned}')

def remove_markdown(text):
    md = MarkdownIt()
    tokens = md.parse(text)
    return " ".join(token.content for token in tokens if token.type == "inline")


def format_bytes(size):
    """
    Convert byte size to a human-readable format.

    Args:
    size (int): Size in bytes.

    Returns:
    str: Formatted size string.
    """
    # Definire le unità
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0

    # Riduci la dimensione fino a raggiungere la dimensione desiderata
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1

    # Restituisci la dimensione formattata
    return f"{size:.2f} {units[i]}"

