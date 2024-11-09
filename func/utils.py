"""
Utility functions for file handling, including permission checks, file moving,
logging, and corruption checking.
"""
import asyncio
import glob
import json
import mimetypes
import os
import shutil
import re

from pathlib import Path
from typing import AnyStr

import ffmpeg
from telethon.errors import MessageNotModifiedError

from classes.attribute_object import AttributeObject
from classes.string_builder import (StringBuilder, LINE_FOR_INFO_DATA,
                                    LINE_FOR_SHOW_LAST_ERROR, TYPE_ACQUIRED,
                                    LINE_FOR_FILE_DIMENSION, LINE_FOR_PINNED_VIDEO,
                                    LINE_FOR_VIDEO_NAME,
                                    LINE_FOR_FILE_NAME, LINE_FOR_FILE_SIZE, TYPE_ERROR, TYPE_COMPLETED)
from func.messages import t
from func.rules import apply_rules, reload_rules
from classes.object_data import ObjectData
from run import PERSONAL_CHAT_ID

VIDEO_EXTENSIONS = (
    ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpv']
)


def check_folder_permissions(folder_path: str):
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


def is_video_file(file_name: str) -> bool:
    """Check if the file has a video extension."""
    _, ext = os.path.splitext(file_name)
    return ext.lower() in VIDEO_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """
    Remove or replace characters in the filename that are not allowed in file names
    on most operating systems, such as <, >, :, \", /, \\, |, ?, *, etc.
    This function also removes any non-alphanumeric characters, except for dots,
    hyphens, and underscores.
    """
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized_name = re.sub(r'[^\w\s.-]', '', sanitized_name)
    return sanitized_name.strip()

def sanitize_video_name(video_name: str) -> str:
    """
    Remove or replace characters in the filename that are not allowed in file names
    on most operating systems, such as <, >, :, \", /, \\, |, ?, *, etc.
    This function also removes any non-alphanumeric characters, except for dots,
    hyphens, and underscores.
    """
    sanitized_name = re.sub(r'[^\w\s.-]', '', video_name)
    sanitized_name = re.sub(r'\s+', ' ', sanitized_name)
    return sanitized_name.strip()


async def move_file(src: Path, dest: Path, cb=None) -> bool:
    """
    Move a file from the source path to the destination path.
    If the move is successful, return True. If an error occurs during the move,
    print an error message and return False.
    """
    try:
        dest_file_name = dest.name
        dest_file_name_without_ext = dest.stem

        if dest_file_name.endswith('.mpv'):
            dest_file_name = os.path.splitext(dest_file_name)[0] + '.mp4'

        base_dest_dir = dest.parent

        dest_dir = base_dest_dir / dest_file_name_without_ext
        dest_dir.mkdir(parents=True, exist_ok=True)

        final_dest = dest_dir / dest_file_name

        shutil.move(str(src), str(final_dest))
        print(t('video_saved_and_moved', final_dest))
        if cb is not None:
            try:
                await cb(src, final_dest, True)
            except (PermissionError, FileNotFoundError):
                reload_rules()
                if cb is not None:
                    await cb(src, None, False)
                return False
        return True
    except (shutil.Error, OSError, FileNotFoundError):
        print(t('error_move_file', os.path.basename(src)))
        reload_rules()
        if cb is not None:
            await cb(src, None, False)
        return False


def is_file_corrupted(file_path: str, total_file_size: int) -> bool:
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

async def compress_video_h265(input_file: Path, output_file: Path, crf=28, callback: callable(AnyStr | None) = None) -> bool:
    """
    Convert a video file from h264 to h265 using ffmpeg.
    If the conversion is successful, return True. If an error occurs during the conversion,
    print an error message and return False.
    """
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"Existing old file converted removed: {output_file}")
    try:
        process = (
            ffmpeg
            .input(str(input_file))
            .output(str(output_file), vcodec='libx265', crf=crf,
                    preset='slow', tune='zerolatency', progress='pipe')
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
    except Exception as exception:  # pylint: disable=broad-exception-caught
        print(f"Error during the compression: {str(exception)}")
        return False


async def download_complete_action(video: ObjectData) -> None:
    """
    Download complete action.
    """
    from func.config import load_configuration
    config = load_configuration()

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
        await add_line_to_text(video.message_id_reference, t('trace_compress_action', time_info),
                               LINE_FOR_INFO_DATA)

    if config.enable_video_compression:
        print(t('start_compress_file', file_path_source))

        await add_line_to_text(video.message_id_reference, t('start_compress_file', str(file_path_source)[:44]),
                               LINE_FOR_INFO_DATA)
        file_path_c = Path(str(video.file_path))
        converted_file_path = file_path_c.with_name(
            file_path_c.stem + "_converted" + file_path_c.suffix)
        if await compress_video_h265(file_path_source, converted_file_path, config.compression_ratio,
                                     compression_message):
            file_path_source.unlink()
            file_path_source = converted_file_path
            print(t('complete_compress_file', file_path_source))
            await add_line_to_text(video.message_id_reference, t('complete_compress_file', str(file_path_source)[:44]),
                                   LINE_FOR_INFO_DATA)
        else:
            print(t('cant_compress_file', file_path_source))
            await add_line_to_text(video.message_id_reference, t('cant_compress_file', str(file_path_source)[:44]),
                                   LINE_FOR_SHOW_LAST_ERROR)
            raise Exception(t('cant_compress_file', file_path_source))  # pylint: disable=broad-exception-raised

    await add_line_to_text(video.message_id_reference, t('ready_to_move', str(file_path_dest)[:44]),
                           LINE_FOR_INFO_DATA)

    print(t('ready_to_move', video.video_name_cleaned))

    async def cb_move_file(src, target, result):
        if result:
            complete_data_file(video)
            await add_line_to_text(video.message_id_reference, t('download_complete', str(target)[:44]),
                                   LINE_FOR_INFO_DATA)
            await define_label(video.message_id_reference, TYPE_COMPLETED)
            if video.is_forward_chat_protected is not True:
                remove_video_data(video)
        else:
            await add_line_to_text(video.message_id_reference, t('error_move_file', str(target)[:44]),
                                   LINE_FOR_SHOW_LAST_ERROR)
            await define_label(video.message_id_reference, TYPE_ERROR)

    await move_file(file_path_source, file_path_dest, cb_move_file)


def remove_video_data(video: ObjectData):
    """
    Remove the video data file based on the video object.
    """
    if os.path.isfile(get_video_data_full_path(video)):
        os.remove(str(get_video_data_full_path(video)))


def remove_video_data_by_video_id(video_id: str):
    """
    Remove the video data file based on the video id.
    """
    files = glob.glob(f"{get_video_data_path()}/*_{video_id}.json")
    for file in files:
        os.remove(str(file))


def video_data_file_exists_by_ref_msg_id(message_id_ref: int):
    """
    Check if the video data file exists based on the message id reference.
    """
    files = glob.glob(f"{get_video_data_path()}/{message_id_ref}_*.json")
    return bool(files)


def video_data_file_exists_by_video_id(video_id: str):
    """
    Check if the video data file exists based on the video id.
    """
    files = glob.glob(f"{get_video_data_path()}/*_{video_id}.json")
    return bool(files)


def get_video_data_name(video: ObjectData):
    """
    Returns the name of the video data file based on the video object.
    """
    from main import client
    return f"{video.message_id_reference}_{client.api_id}_{video.chat_id}_{video.id}.json"


def get_video_data_full_path(video: ObjectData):
    """
    Returns the full path of the video data file based on the video object.
    """
    if os.path.isdir(get_video_data_path()) is False:
        os.mkdir(get_video_data_path())
    return os.path.join(get_video_data_path(), get_video_data_name(video))


def get_video_data_path() -> str:
    """
    Returns the path of the video data folder.
    """
    from run import root_dir
    return os.path.join(root_dir, 'videos_data')


def complete_data_file(video: ObjectData) -> None:
    """
    Complete the video data file.
    """
    save_video_data({'completed': True}, video, ['completed'])


def load_config(file_path: str):
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


def safe_getattr(obj, attr, default=''):
    """
    Restituisce il valore dell'attributo se esiste, altrimenti restituisce un valore di default.
    Gestisce anche i casi in cui l'attributo non è una stringa o è None.
    """
    value = getattr(obj, attr, default)

    # Se il valore non è una stringa o è None, restituisci una stringa vuota
    if not isinstance(value, str):
        return ''
    return value

async def add_line_to_text(message_id: str, new_line: str, line_number: int, with_default_icon: bool = False) -> None:
    """
    Add a new line to the text of the reference message.
    """
    from run import LOG_IN_PERSONAL_CHAT
    from func.main import client
    # Divide il testo in righe

    message = await client.get_messages(PERSONAL_CHAT_ID, ids=message_id) # get realtime info
    text = message.text

    builder = StringBuilder(text)
    builder.edit_in_line(new_line, line_number, with_default_icon)

    # Unisce di nuovo le righe in una singola stringa
    if LOG_IN_PERSONAL_CHAT is True and message is not None:
        try:
            await message.edit(builder.string)
        except (MessageNotModifiedError, PermissionError) as er:
            print(er.message)
            pass

async def define_label(message_id: str, label) -> None:
    """
    Add a new line to the text of the reference message.
    """
    from run import LOG_IN_PERSONAL_CHAT
    from func.main import client

    message = await client.get_messages(PERSONAL_CHAT_ID, ids=message_id)  # get realtime info
    text = message.text

    # Divide il testo in righe
    builder = StringBuilder(text)
    builder.define_label(label)

    # Unisce di nuovo le righe in una singola stringa
    if LOG_IN_PERSONAL_CHAT is True and message is not None:
        try:
            await message.edit(builder.string)
        except (MessageNotModifiedError, PermissionError) as er:
            print(er.message)
            pass


def save_video_data(data: dict, video: ObjectData, fields_to_compare=None) -> bool:
    """
    Save the video data in a JSON file.
    If the file already exists, compare the data with the existing data and only save the differences.
    """
    file_path = get_video_data_full_path(video)
    data_keys = list(data.keys())
    data = ObjectData(**data)

    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            try:
                existing_data = json.load(f)
            except EOFError:
                print(f"Errore nel caricamento di {file_path}: il file è vuoto o corrotto.")
                existing_data = None

        if existing_data is None:
            existing_data = data
        else:
            existing_data = ObjectData(**existing_data)
            if fields_to_compare:
                data_subset = {field: getattr(data, field, None) for field in fields_to_compare}
                existing_data_subset = ({field: getattr(existing_data, field, None)
                                         for field in fields_to_compare})

                # Se i campi specificati sono identici, controlla anche per i campi non specificati
                if data_subset == existing_data_subset:
                    # Aggiorna i campi rimanenti anche se i campi specificati sono uguali
                    for field in data_keys:
                        if field not in fields_to_compare:
                            if getattr(data, field) is not None:
                                setattr(existing_data, field, getattr(data, field))
                else:
                    # Se ci sono differenze nei campi specificati, aggiorna
                    for field in data_keys:
                        setattr(existing_data, field, getattr(data, field))
            else:
                # Confronto di tutto l'oggetto se non sono stati specificati campi
                if data == existing_data:
                    print("Nessuna differenza trovata, dati non salvati.")
                    return False
    else:
        # Se il file non esiste, usa i nuovi dati
        existing_data = data
    # Salva solo se ci sono differenze
    with open(file_path, "wb") as f:
        f.write(json.dumps(existing_data, default=serialize).encode('utf-8'))
    print("Dati salvati con successo.")
    return True


def serialize(obj: ObjectData):
    """
    Serialize an object to JSON.

    Args:
        obj (ObjectData): The object to serialize.

    Returns:
        dict: The serialized object.
    """
    if isinstance(obj, (ObjectData, AttributeObject)):
        default_obj = type(obj)()
        serialized_data = {}
        for field, value in vars(default_obj).items():
            serialized_data[field] = getattr(obj, field, value) or value
        return serialized_data
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def default_video_message(video: ObjectData):
    """
    Generate the default message for a video.

    Args:
        video (ObjectData): The video data object.

    Returns:
        str: The default message for the video.
    """
    video_text = remove_markdown("".join(video.video_name.splitlines()))[:40]
    file_name = remove_markdown("".join(video.file_name.splitlines()))[:40]

    if video.is_forward_chat_protected is True:
        video_text = f"{video_text} (**Forward Chat Protected**)"

    builder = StringBuilder()
    builder.edit_in_line(f'🎥 **{video_text}**', LINE_FOR_VIDEO_NAME)
    builder.edit_in_line(f'🗃 {file_name}', LINE_FOR_FILE_NAME)
    video_media = getattr(video, 'video_media', None)
    if video_media is not None:
        builder.edit_in_line(f'⚖️ {format_bytes(video_media.document.size)}', LINE_FOR_FILE_SIZE)
    builder.define_label(TYPE_ACQUIRED)
    video_attribute = getattr(video, 'video_attribute', None)
    if video_attribute is not None and hasattr(video_attribute, 'w') and hasattr(video_attribute, 'h'):
        builder.edit_in_line(
            f'{video_attribute.w}x{video_attribute.h}',
            LINE_FOR_FILE_DIMENSION, True)
    builder.edit_in_line(f'📌 {video.pinned}', LINE_FOR_PINNED_VIDEO)

    return builder.string


def remove_markdown(text: str):
    """
    Remove Markdown formatting from a string.

    Args:
    text (str): The string to remove Markdown formatting from.

    Returns:
    str: The string with Markdown formatting removed.
    """
    string_manipulated = re.sub(r'\[([^]]+)]\([^)]+\)', r'\1', text)
    string_manipulated = re.sub(r'([*_~`]+)', '', string_manipulated)
    string_manipulated = re.sub(r'#+ ', '', string_manipulated)
    string_manipulated = re.sub(r'^[*\-+] ', '', string_manipulated, flags=re.MULTILINE)
    return string_manipulated


def format_bytes(size: int):
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
