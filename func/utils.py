"""
Utility functions for file handling, including permission checks, file moving,
logging, and corruption checking.
"""
import glob
import json
import mimetypes
import os
import shutil
import re

from pathlib import Path
from typing import Union

from telethon.errors import MessageNotModifiedError
from telethon.tl.patched import Message
from telethon.tl.types import MessageMediaDocument

from classes.attribute_object import AttributeObject
from func.compression import (COMPRESSION_STATE_COMPRESSION_FAILED_BAD_TRASH_FILE,
                              COMPRESSION_STATE_NOT_COMPRESSED_EXCEED_COMPRESSION_SIZE,
                              COMPRESSION_STATE_COMPRESSION_FAILED_NOT_OUTPUT_FILE)
from classes.string_builder import (StringBuilder, LINE_FOR_INFO_DATA,
                                    LINE_FOR_SHOW_LAST_ERROR, TYPE_ACQUIRED,
                                    LINE_FOR_FILE_DIMENSION, LINE_FOR_PINNED_VIDEO,
                                    LINE_FOR_VIDEO_NAME,
                                    LINE_FOR_FILE_NAME, LINE_FOR_FILE_SIZE, TYPE_ERROR, TYPE_COMPLETED,
                                    LINE_FOR_TARGET_FOLDER, TYPE_COMPRESSING)
from func.messages import t
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
        try:
            os.makedirs(folder_path)
        except OSError:
            print(f"Failed to create directory: {folder_path}")
            return False
    if not os.path.isdir(folder_path):
        raise PermissionError(f"{folder_path} is not a directory.")
    if not os.access(folder_path, os.W_OK):
        raise PermissionError(f"Permission denied: {folder_path}")

    return True


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
                from func.main import rules_object
                rules_object.reload_rules()
                if cb is not None:
                    await cb(src, None, False)
                return False
        return True
    except (shutil.Error, OSError, FileNotFoundError):
        from func.main import rules_object
        print(t('error_move_file', os.path.basename(src)))
        rules_object.reload_rules()
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


def get_inlist_video_object_by_message_id_reference(message_id_reference: str) -> ObjectData | None:
    """
    Get video object by message id reference.
    """
    from func.main import operation_status
    for video in operation_status.videos_data:
        if video is not None:
            if message_id_reference == video[1].message_id_reference:
                return video[1]
    return None


async def download_complete_action(video: ObjectData) -> None:
    """
    Download complete action.
    """
    from func.config import load_configuration
    config = load_configuration()

    mime_type, _ = mimetypes.guess_type(video.file_path)
    extension = mimetypes.guess_extension(mime_type) if mime_type else ''
    if video.video_completed_folder is None:
        raise OSError(t('error_video_completed_folder_none'), video.message_id_reference)

    completed_folder = video.video_completed_folder
    completed_file_path = os.path.join(completed_folder, video.video_name_cleaned + extension)

    file_path_source = Path(str(video.file_path))
    file_path_dest = Path(str(completed_file_path))

    async def compression_message(progress, current_size, remaining_time):
        compressed_file_size = format_bytes(int(current_size))
        num_blocks = int(progress // 20)
        progress_bar = '■' * num_blocks + '░' * (5 - num_blocks)
        progress_bar_display = f"[{progress_bar}] {progress:.2f}%"

        await add_line_to_text(
            video.message_id_reference,
            t('trace_compress_action',
              progress_bar_display,
              compressed_file_size,
              format_time(remaining_time)),
            LINE_FOR_INFO_DATA)

    if config.enable_video_compression:
        print(t('start_compress_file', file_path_source))

        await add_line_to_text(
            video.message_id_reference,
            t('start_compress_file', str(file_path_source)[:44]),
            LINE_FOR_INFO_DATA)
        file_path_c = Path(str(video.file_path))
        converted_file_path = file_path_c.with_name(
            file_path_c.stem + "_converted" + file_path_c.suffix)
        from func.compression import (
            compress_video_h265
        )
        await define_label(video.message_id_reference, TYPE_COMPRESSING)
        compressing_state = await compress_video_h265(
            file_path_source,
            converted_file_path,
            config.compression_ratio,
            config.compression_min_size_mb,
            compression_message)

        file_path_source = \
            await compression_action(compressing_state, video, file_path_source, converted_file_path)


    await add_line_to_text(video.message_id_reference, t('ready_to_move', str(file_path_dest)[:44]),
                           LINE_FOR_INFO_DATA)

    print(t('ready_to_move', video.video_name_cleaned))

    async def cb_move_file(src, target, result):
        if result:
            complete_data_file(video)
            await add_line_to_text(video.message_id_reference, t('download_complete', str(target)[:55]),
                                   LINE_FOR_INFO_DATA)
            await define_label(video.message_id_reference, TYPE_COMPLETED)
            if video.is_forward_chat_protected is not True:
                remove_video_data(video)
        else:
            await add_line_to_text(video.message_id_reference, t('error_move_file', str(target)[:55]),
                                   LINE_FOR_SHOW_LAST_ERROR)
            await define_label(video.message_id_reference, TYPE_ERROR)

    await move_file(file_path_source, file_path_dest, cb_move_file)
    # Unpin message on complete
    from func.main import client
    video_message = await client.get_messages(PERSONAL_CHAT_ID, ids=video.message_id_reference)
    if video_message is not None:
        await video_message.unpin()

def format_time(seconds):
    """
    Convert seconds into a readable format (days, hours, minutes, seconds).
    :param seconds: Time in seconds
    :return: Formatted time string
    """
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{int(days):02}:{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

async def compression_action(
        compressing_state,
        video: ObjectData,
        file_path_source: Path,
        converted_file_path: Path) -> Path:
    """ Compression action. """
    from func.compression import (
        COMPRESSION_STATE_COMPRESSED,
        COMPRESSION_STATE_COMPRESSION_FAILED,
        COMPRESSION_STATE_NOT_COMPRESSED
    )
    if compressing_state == COMPRESSION_STATE_COMPRESSED:
        converted_file_size = os.path.getsize(converted_file_path)
        converted_file_size_formatted = format_bytes(int(converted_file_size))
        print(t('complete_compress_file', file_path_source, converted_file_size_formatted))
        await add_line_to_text(
            video.message_id_reference,
            f"{format_bytes(video.video_media.document.size)} ({converted_file_size_formatted})",
            LINE_FOR_FILE_SIZE, True)
        await add_line_to_text(video.message_id_reference,
                               t('complete_compress_file',
                                 str(file_path_source)[:44],
                                 converted_file_size_formatted),
                               LINE_FOR_INFO_DATA)
        file_path_source.unlink()
        file_path_source = converted_file_path
        return file_path_source

    if compressing_state == COMPRESSION_STATE_COMPRESSION_FAILED_BAD_TRASH_FILE:
        print(t('old_compress_file', file_path_source))
        await add_line_to_text(video.message_id_reference,
                               t('old_compress_file', str(file_path_source)[:44]),
                               LINE_FOR_SHOW_LAST_ERROR)
        raise Exception(t('old_compress_file',  # pylint: disable=broad-exception-raised
                          file_path_source))
    if compressing_state == COMPRESSION_STATE_COMPRESSION_FAILED_NOT_OUTPUT_FILE:
        print(t('error_output_compress_file', file_path_source))
        await add_line_to_text(video.message_id_reference,
                               t('error_output_compress_file', str(file_path_source)[:44]),
                               LINE_FOR_SHOW_LAST_ERROR)
        raise Exception(t('error_output_compress_file',  # pylint: disable=broad-exception-raised
                          file_path_source))
    if compressing_state == COMPRESSION_STATE_NOT_COMPRESSED_EXCEED_COMPRESSION_SIZE:
        print(t('exceed_compress_file', file_path_source))
        await add_line_to_text(video.message_id_reference,
                               t('exceed_compress_file', str(file_path_source)[:44]),
                               LINE_FOR_SHOW_LAST_ERROR)
    if compressing_state == COMPRESSION_STATE_COMPRESSION_FAILED:
        print(t('cant_compress_file', file_path_source))
        await add_line_to_text(video.message_id_reference,
                               t('cant_compress_file', str(file_path_source)[:44]),
                               LINE_FOR_SHOW_LAST_ERROR)
        raise Exception(t('cant_compress_file',  # pylint: disable=broad-exception-raised
                          file_path_source))
    if compressing_state is COMPRESSION_STATE_NOT_COMPRESSED:
        print(t('skip_compress_file', file_path_source))
        await add_line_to_text(video.message_id_reference,
                               t('skip_compress_file', str(file_path_source)[:44]),
                               LINE_FOR_INFO_DATA)

    return file_path_source

def remove_video_data(video_object: ObjectData) -> None:
    """
    Remove the video data file based on the video object.
    """
    from func.main import operation_status
    if video_object is None:
        return
    if os.path.isfile(get_video_data_full_path(video_object)):
        os.remove(str(get_video_data_full_path(video_object)))
        # Removes from videos_data
        videos_data = operation_status.videos_data
        operation_status.videos_data = [
            (file_name, obj_data) for file_name, obj_data in videos_data if obj_data.id != video_object.id
        ]


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


def get_video_data_name(message_id_reference: int, chat_id: int, video_id: int):
    """
    Returns the name of the video data file based on the video object.
    """
    from main import client
    return f"{message_id_reference}_{client.api_id}_{chat_id}_{video_id}.json"


def get_video_data_full_path(video: ObjectData):
    """
    Returns the full path of the video data file based on the video object.
    """
    if os.path.isdir(get_video_data_path()) is False:
        os.mkdir(get_video_data_path())
    return os.path.join(
        get_video_data_path(),
        get_video_data_name(
            video.message_id_reference, video.chat_id, video.video_id)
    )


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


async def add_line_to_text(
        message_id: str | int,
        new_line: str,
        line_number: int,
        with_default_icon: bool = False
) -> None:
    """
    Add a new line to the text of the reference message.
    """
    from run import LOG_IN_PERSONAL_CHAT
    from func.main import client
    # Divide il testo in righe
    if isinstance(message_id, str):
        message_id = int(message_id)

    message = await client.get_messages(PERSONAL_CHAT_ID, ids=message_id)  # get realtime info
    text = message.text

    builder = StringBuilder(text)
    new_line = new_line.replace('\n', ' ')
    builder.edit_in_line(new_line, line_number, with_default_icon)

    # Unisce di nuovo le righe in una singola stringa
    if LOG_IN_PERSONAL_CHAT is True and message is not None:
        try:
            await message.edit(builder.string)
        except (MessageNotModifiedError, PermissionError) as er:
            print(er.message)


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


async def get_video_status_label(message_reference: int | Union[Message, MessageMediaDocument]):
    """
    Get the status label of the video.
    :param message_reference:
    :return:
    """
    from func.main import client

    if isinstance(message_reference, int):
        message = await client.get_messages(PERSONAL_CHAT_ID, ids=message_reference)
    elif isinstance(message_reference, (Message, MessageMediaDocument)):
        message = message_reference
    else:
        return None

    text = message.text
    string_object = StringBuilder(text)
    return string_object.get_label()


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

                if data_subset == existing_data_subset:
                    for field in data_keys:
                        if field not in fields_to_compare:
                            if getattr(data, field) is not None:
                                setattr(existing_data, field, getattr(data, field))
                else:
                    for field in data_keys:
                        setattr(existing_data, field, getattr(data, field))
            else:
                if data == existing_data:
                    print("Nessuna differenza trovata, dati non salvati.")
                    return False
    else:
        existing_data = data
    try:
        with open(file_path, "wb") as f:
            f.write(json.dumps(existing_data, default=serialize).encode('utf-8'))
        return True
    except PermissionError as e:
        print(f"Errore di permessi per il file: {file_path}. Dettagli: {e}")
        raise
    except Exception as e:
        print(f"Errore generico: {e}")
        raise


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


def default_video_message(video_object: ObjectData):
    """
    Generate the default message for a video.

    Args:
        video_object (ObjectData): The video data object.

    Returns:
        str: The default message for the video.
        :param video_object:
    """
    from func.main import configuration
    video_text = remove_markdown("".join(video_object.video_name.splitlines()))[:40]
    file_name = remove_markdown("".join(video_object.file_name.splitlines()))[:40]

    if video_object.is_forward_chat_protected is True:
        video_text = f"{video_text} (**Forward Chat Protected**)"

    completed_folder_path = video_object.video_completed_folder or configuration.completed_folder
    reduced_path_name = reduce_path_action(completed_folder_path)

    builder = StringBuilder()
    builder.edit_in_line('---', LINE_FOR_INFO_DATA)
    builder.edit_in_line(f'**{video_text}**', LINE_FOR_VIDEO_NAME, True)
    builder.edit_in_line(file_name, LINE_FOR_FILE_NAME, True)
    builder.edit_in_line(reduced_path_name, LINE_FOR_TARGET_FOLDER, True)
    video_media = getattr(video_object, 'video_media', None)
    if video_media is not None:
        if configuration.enable_video_compression is True:
            from func.compression import compression_ratio_calc
            compression_size = \
                compression_ratio_calc(video_media.document.size, configuration.compression_ratio)
            size_and_compression_size = \
                f"{format_bytes(video_media.document.size)} (~{format_bytes(int(compression_size))})" \
                    if compression_size is not None \
                    else format_bytes(video_media.document.size)
            builder.edit_in_line(size_and_compression_size, LINE_FOR_FILE_SIZE, True)
        else:
            builder.edit_in_line(format_bytes(video_media.document.size), LINE_FOR_FILE_SIZE, True)
    builder.define_label(TYPE_ACQUIRED)
    video_attribute = getattr(video_object, 'video_attribute', None)
    if video_attribute is not None and hasattr(video_attribute, 'w') and hasattr(video_attribute, 'h'):
        builder.edit_in_line(
            f'{video_attribute.w}x{video_attribute.h}',
            LINE_FOR_FILE_DIMENSION, True)
    builder.edit_in_line(video_object.pinned, LINE_FOR_PINNED_VIDEO, True)

    return builder.string


def reduce_path_action(path: str, max_length: int = 4) -> str:
    """
    Reduce each part of a path to a maximum length, keeping the final part intact.

    Args:
        path (str): The path to reduce.
        max_length (int): The maximum length of each reduced part (except the final one).

    Returns:
        str: The reduced path.
    """
    if len(path) <= max_length:
        return path

    parts = [part for part in path.split(os.sep) if part]
    final_part = parts.pop() if parts else ""
    reduced_parts = [part[:max_length] + "..." if len(part) > max_length else part for part in parts]
    reduced_path = os.sep.join(reduced_parts + [final_part])

    if path.startswith(os.sep):
        reduced_path = os.sep + reduced_path
    if path.endswith(os.sep):
        reduced_path += os.sep

    return reduced_path


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


def validate_and_check_path(path):
    """
    Check if a path is valid and exists.

    Args:
        path (str): The path to check.

    Returns:
        dict: A dictionary containing the validation result.
    """
    result = {"is_valid_format": False, "exists": False, "error": None}

    try:
        if not isinstance(path, str) or path.strip() == "":
            result["error"] = "Path is not a string or is empty."
            return result

        normalized_path = os.path.normpath(path)

        if any(char in path for char in ['<', '>', ':', '"', '|', '?', '*']):
            result["error"] = "Path contains invalid characters."
            return result

        result["is_valid_format"] = True

        result["exists"] = os.path.exists(normalized_path)

    except Exception as e:  # pylint: disable=broad-exception-caught
        result["error"] = f"Error validating and checking path: {str(e)}"

    return result


def is_valid_folder(path):
    """
    Check if a path is a valid folder.
    Args:
        path (str): The path to check.

    Returns:
        bool: True if the path is a valid folder, False otherwise.
    """
    base_name = os.path.basename(path)
    _, extension = os.path.splitext(base_name)

    return extension == ""


def detect_remaining_size_in_disk_by_path(path, file_size, threshold_percentage=10):
    """
    Detect the remaining size in disk by path, considering the size of a file, and analyze its usage.

    Args:
        path (str): The path to detect the remaining size in disk.
        file_size (int): The size of the file to consider in bytes.
        threshold_percentage (float): The percentage threshold to evaluate space availability.

    Returns:
        dict: A dictionary containing:
            - free_space_bytes (int): The remaining size in disk in bytes after considering the file.
            - free_space_percentage (float): The remaining size in percentage after considering the file.
            - free_space_format (str): The remaining size in disk in a human-readable format.
            - exceeds_threshold (bool): True if free space percentage is lower than or equal to the threshold.
            - can_fit_file (bool): True if the file can fit in the remaining space.
    """
    if not os.path.exists(path):
        return {
            "free_space_bytes": 0,
            "free_space_format": "0 B",
            "free_space_percentage": 0,
            "exceeds_threshold": False,
            "can_fit_file": False,
        }
    total, _, free = shutil.disk_usage(path)

    # Calcola lo spazio libero considerando il file
    remaining_space = free - file_size
    remaining_space_percentage = round((remaining_space / total) * 100, 2) if remaining_space > 0 else 0

    exceeds_threshold = remaining_space_percentage <= 100 - threshold_percentage
    can_fit_file = remaining_space >= 0

    return {
        "free_space_bytes": remaining_space,
        "free_space_format": format_bytes(remaining_space),
        "free_space_percentage": remaining_space_percentage,
        "exceeds_threshold": exceeds_threshold,
        "can_fit_file": can_fit_file,
    }
