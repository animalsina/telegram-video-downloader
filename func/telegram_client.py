"""
Module for interacting with Telegram API to download files with progress tracking and retry logic.
"""
import json
import time
import os
import asyncio
import collections
from pathlib import Path
from xmlrpc.client import MAXINT

from telethon import TelegramClient
from telethon.errors import FloodError
from telethon.tl.patched import Message
from tqdm import tqdm

from classes.attribute_object import AttributeObject
from classes.custom_flood_error import CustomFloodError
from classes.object_data import ObjectData
from classes.string_builder import TYPE_CANCELLED, TYPE_ACQUIRED, TYPE_DOWNLOADING
from classes.tqdm_object import TqdmObject
from func.messages import t
from func.save_video_data_action import change_target_folder
from func.utils import (
    is_file_corrupted, download_complete_action, add_line_to_text, LINE_FOR_INFO_DATA,
    LINE_FOR_SHOW_LAST_ERROR, get_video_data_path, define_label, detect_remaining_size_in_disk_by_path)


def calculate_download_speed(current: int, time_elapsed: float, last_current: int):
    """Calculate download speed."""
    if time_elapsed <= 0:
        return 0
    return (current - last_current) / time_elapsed


async def edit_service_message(message: Message, text, time_to_expire=10):
    """
    Edit service message, self-destruct after {time_to_expire} seconds
    :param message:
    :param text:
    :param time_to_expire:
    :return:
    """

    async def delete():
        await asyncio.sleep(time_to_expire)
        return await message.delete()

    asyncio.create_task(delete())
    await message.edit(text)


async def send_service_message(chat_id, text, time_to_expire=10):
    """
    Service message, self-destruct after {time_to_expire} seconds
    :param chat_id:
    :param text:
    :param time_to_expire:
    :return:
    """
    from func.main import client, configuration
    if client.is_connected() is False:
        client.start(configuration.phone)
    message = await client.send_message(chat_id, text)

    async def delete():
        await asyncio.sleep(time_to_expire)
        return await message.delete()

    asyncio.create_task(delete())
    return message


def create_telegram_client(session_name: str, api_id: int, api_hash: str):
    """Create and return a new TelegramClient."""
    return TelegramClient(session_name, api_id, api_hash)


async def update_download_message(message_id: str, percent: float, time_remaining_formatted: str):
    """Update the status message with the download progress and time remaining."""
    await add_line_to_text(message_id,
                           f"⬇️ Download: {percent:.2f}% - {time_remaining_formatted}",
                           LINE_FOR_INFO_DATA)


def format_time(seconds: float) -> str:
    """Format time in seconds to a human-readable string like hh:mm:ss."""
    if seconds <= 0 or seconds == float('inf'):
        return "Calculating..."

    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


tqdm_config = TqdmObject({
    'last_current': 0,
    'last_update_time': 0
})


async def progress_tracking(
        progress: int,
        file_size: int,
        video: ObjectData,
        temp_file_path: str,
        attempt: int,
        retry_attempts: int
):
    """
    Track the download progress and update the status message.
    """

    await add_line_to_text(video.message_id_reference, '', LINE_FOR_SHOW_LAST_ERROR, False)

    # Initialize the progress bar
    with tqdm(total=file_size, initial=progress,
              desc=f"Downloading {video.video_id} - {video.file_name} -"
                   f" {video.video_name_cleaned}",
              unit='B', unit_scale=True, unit_divisor=1024) as pbar:
        # Download the media to the temp file using iter_download
        await download_with_rate_limit(
            pbar,
            video,
            progress,
            file_size,
            temp_file_path,
            attempt,
            retry_attempts)


async def progress_callback(
        video: ObjectData,
        pbar: tqdm,
        current: int,
        total: int,
        speed_samples: collections.deque
):
    """
    Callback function to update the progress bar and status message.
    :param video:
    :param pbar:
    :param current:
    :param total:
    :param speed_samples:
    :return:
    """

    if total is not None:

        if is_interrupted() is True:
            print(t('download_stopped'))
            await add_line_to_text(video.message_id_reference,
                                   t('download_stopped'),
                                   LINE_FOR_INFO_DATA, True)
            raise KeyboardInterrupt(t('download_stopped'))

        percent_complete: float = (current / total) * 100
        current_time: float = time.time()

        # Calculate time elapsed
        time_elapsed: float = current_time - tqdm_config.last_update_time

        # Calculate download speed
        download_speed: float | int = calculate_download_speed(
            current,
            time_elapsed,
            tqdm_config.last_current
        )

        # Add the current speed to the speed sample buffer
        speed_samples.append(download_speed)

        # Calculate average speed for a more accurate estimate
        average_speed: float = (sum(speed_samples) / len(speed_samples)
                                if speed_samples else 0)
        time_remaining: float = ((total - current) / average_speed
                                 if average_speed > 0 else float('inf'))

        # Update the status message every 3 seconds
        if current_time - tqdm_config.last_update_time >= 3:
            time_remaining_formatted = format_time(time_remaining)
            await update_download_message(video.message_id_reference,
                                          percent_complete,
                                          time_remaining_formatted)
            tqdm_config.last_update_time = current_time
            tqdm_config.last_current = current

        # Update the progress bar
        pbar.update(current - pbar.n)
        pbar.total = total
        pbar.n = current


async def download_with_rate_limit(
        pbar: tqdm,
        video: ObjectData,
        progress: int,
        file_size: int,
        temp_file_path: str,
        attempt: int,
        retry_attempts: int
):
    """
    Download the media to the temp file using iter_download
    :param retry_attempts:
    :param attempt:
    :param pbar:
    :param video:
    :param progress:
    :param file_size:
    :param temp_file_path:
    :return:
    """
    from func.main import client, operation_status, configuration

    kb_download = min(256, configuration.max_download_size_request_limit_kb)

    if operation_status.is_premium is True:
        kb_download = configuration.max_download_size_request_limit_kb \
            if configuration.max_download_size_request_limit_kb != -1 else MAXINT

    # Buffer to store speed data samples
    speed_samples = collections.deque(maxlen=20)

    try:
        download_iter = client.iter_download(
            video.video_media, offset=progress,
            request_size=kb_download * 1024)
        if operation_status.interrupt is True:
            return

        directory = os.path.dirname(temp_file_path)
        Path(directory).mkdir(parents=True, exist_ok=True)

        if not os.path.exists(temp_file_path):
            with open(temp_file_path, 'wb'):
                pass

        with open(temp_file_path, 'ab') as f:
            async for chunk in download_iter:
                if operation_status.interrupt is True:
                    return
                f.write(chunk)
                await progress_callback(video, pbar, f.tell(), file_size, speed_samples)
                sleep_time = 0.5 + (2 - 0.5) * (min(1 - attempt, 0) / retry_attempts)
                await asyncio.sleep(sleep_time)

            await asyncio.sleep(5)
    except FloodError as e:
        print(e)
        raise CustomFloodError(e.message) from e
    except Exception as e:  # pylint: disable=broad-except
        print(e)
        raise


async def get_user_id():
    """
    Get user id
    """
    return (await get_user_data()).id


async def get_user_data():
    """
    Get user data
    """
    from func.main import configuration
    from func.main import client
    if client.is_connected() is False:
        client.start(configuration.phone)
    return await client.get_me()


def is_interrupted():
    """
    Check if the download is interrupted
    :return:
    """
    from func.main import operation_status
    return (operation_status.interrupt is True or
            operation_status.quit_program is True or
            operation_status.start_download is not True)


async def check_completed_folder_exist(video):
    """
    Check completed folder exist for video, if it doesn't exist, it will generate an exception
    and adds an error message in the video caption
    :param video:
    :return:
    """
    from command.download import get_completed_task_folder_path
    if get_completed_task_folder_path(video) is not None:
        try:
            os.makedirs(get_completed_task_folder_path(video), exist_ok=True)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        if os.path.exists(get_completed_task_folder_path(video)) is False:
            await add_line_to_text(
                video.message_id_reference,
                t('folder_not_exist', video.file_name),
                LINE_FOR_SHOW_LAST_ERROR,
                True)
            raise Exception(  # pylint: disable=broad-exception-raised
                t(
                    'folder_not_exist',
                    get_completed_task_folder_path(video)
                )
            )


async def reassign_video_folder_completed(video_data: ObjectData):
    """
    Reassign the video to the completed folder
    """
    from command.download import get_completed_task_folder_path
    video_completed_folder = get_completed_task_folder_path(video_data)
    if video_completed_folder is not None:
        await change_target_folder(video_data.message_id_reference, video_completed_folder)

# pylint: disable=too-many-statements
async def download_with_retry(client: TelegramClient, video: ObjectData,
                              retry_attempts: int = 20):  # pylint: disable=too-many-statements
    """Download a file with retry attempts in case of failure."""
    from run import PERSONAL_CHAT_ID

    # Here checks for video data, because if video is stored during the iteration, it will expire
    video_message_data = await client.get_messages(
        PERSONAL_CHAT_ID,
        ids=video.message_id_reference
    )  # type: Message

    if video_message_data is None:
        print(t('download_stopped'))
        return

    if video.is_forward_chat_protected is not True:
        video.video_media = video_message_data.media
    else:
        video_data = \
            await client.get_messages(video.chat_name, ids=video.video_id)  # type: Message
        video.video_media = video_data.media

    attempt = 0
    progress = 0
    tqdm_config.last_current = 0
    tqdm_config.last_update_time = time.time()
    file_size = video.video_media.document.size
    temp_file_path = f"{video.file_path}.temp"

    # Reassign the video folder
    await reassign_video_folder_completed(video)

    while attempt < retry_attempts:
        try:
            if await validate_download(temp_file_path, file_size, video):
                break

            # At this point the folder must be existed
            await check_completed_folder_exist(video)
            # Start to pin the message
            await video_message_data.pin()
            if os.path.exists(temp_file_path):
                progress = os.path.getsize(temp_file_path)

            # Check if the disk space limit is exceeded for the completed folder
            if await check_valid_disk_space_limit(
                    video,
                    file_size,
                    video.video_completed_folder) is False:
                break

            # Check if the disk space limit is exceeded for the temp file
            if await check_valid_disk_space_limit(
                    video,
                    file_size,
                    os.path.dirname(video.file_path)) is False:
                break

            # Download the file with progress tracking
            await define_label(video.message_id_reference, TYPE_DOWNLOADING)
            await progress_tracking(progress, file_size, video, temp_file_path, attempt, retry_attempts)
            # Wait 3 seconds before to get temp file size
            await asyncio.sleep(3)
            await define_label(video.message_id_reference, TYPE_ACQUIRED)

            if is_interrupted() is True:
                print(t('download_stopped', video.file_name))
                await add_line_to_text(video.message_id_reference,
                                       t('download_stopped', video.file_name),
                                       LINE_FOR_INFO_DATA, True)
                break

        except CustomFloodError as e:
            attempt += 1
            wait_time = await attempt_message(e, attempt, retry_attempts, video)
            if attempt == retry_attempts:
                await define_label(video.message_id_reference, TYPE_CANCELLED)
                await add_line_to_text(
                    video.message_id_reference,
                    t('download_error', video.file_name),
                    LINE_FOR_SHOW_LAST_ERROR,
                    True
                )
            await video_message_data.unpin()
            await asyncio.sleep(wait_time)

        except (OSError, IOError) as e:
            print(f"File system error: {str(e)}")
            await video_message_data.unpin()
            await define_label(video.message_id_reference, TYPE_CANCELLED)
            await add_line_to_text(video.message_id_reference, t('file_system_error', str(e)),
                                   LINE_FOR_SHOW_LAST_ERROR)
            break

        except Exception as error:  # pylint: disable=broad-exception-caught
            print(f"Unexpected error: {str(error)}")
            await video_message_data.unpin()
            await define_label(video.message_id_reference, TYPE_CANCELLED)
            await add_line_to_text(video.message_id_reference, f"Unexpected error: {str(error)}",
                                   LINE_FOR_SHOW_LAST_ERROR)
            break


async def check_valid_disk_space_limit(video: ObjectData, file_size: int, target_folder_path: str) -> bool:
    """
    Check if the disk space limit is exceeded
    :param video:
    :param file_size:
    :param target_folder_path:
    :return:
    """
    from func.main import configuration
    from func.utils import is_valid_folder

    if not os.path.exists(target_folder_path) and is_valid_folder(target_folder_path) is True:
        os.mkdir(target_folder_path)

    disk_info_target = detect_remaining_size_in_disk_by_path(
        target_folder_path,
        file_size,
        configuration.disk_space_limit_percentage)
    if disk_info_target['exceeds_threshold'] is True:
        await define_label(video.message_id_reference, TYPE_CANCELLED)
        await add_line_to_text(
            video.message_id_reference,
            t('download_blocked_by_disk_space_limit',
              disk_info_target['free_space_percentage'],
              100 - configuration.disk_space_limit_percentage,
              target_folder_path,
              disk_info_target['free_space_format']),
            LINE_FOR_SHOW_LAST_ERROR,
            True
        )
        from func.main import operation_status
        operation_status.start_download = False
        operation_status.interrupt = True
        return False

    return True


async def validate_download(temp_file_path, file_size, video):
    """
    :param temp_file_path:
    :param file_size:
    :param video:
    :return:
    """
    tolerance = 0  # bytes
    if os.path.exists(temp_file_path):
        temp_file_size = os.path.getsize(temp_file_path)
    else:
        temp_file_size = 0

    if os.path.exists(video.file_path) and not is_file_corrupted(video.file_path, file_size):
        await download_complete_action(video)
        return True

    if abs(temp_file_size - file_size) <= tolerance:
        os.rename(temp_file_path, video.file_path)
        print(f"Downloaded video to: {video.file_path}")
        if os.path.exists(video.file_path) and not is_file_corrupted(video.file_path, file_size):
            await download_complete_action(video)
            return True
        return False

    if temp_file_size > file_size:
        os.remove(temp_file_path)
        await add_line_to_text(
            video.message_id_reference,
            t('corrupted_file', video.file_name), LINE_FOR_SHOW_LAST_ERROR)
        print(t('corrupted_file', video.file_name))
    return False


async def attempt_message(error_message, attempt, retry_attempts, video):
    """
    :param error_message:
    :param attempt:
    :param retry_attempts:
    :param video:
    :return:
    """
    wait_time = 10  # Add a buffer time for safety
    if isinstance(error_message, CustomFloodError):
        message = error_message.message
        if message is not None:
            wait_time = int(
                message.replace("FLOOD_PREMIUM_WAIT_", "")
            ) + 1 if message.startswith("FLOOD_PREMIUM_WAIT_") else 10
    print(
        f"Rate limit exceeded. Waiting for some {wait_time} seconds before retrying..."
        f" Remaining attempts: {attempt} on {retry_attempts}")
    print("Exception: " + str(error_message))
    await add_line_to_text(video.message_id_reference,
                           t('rate_limit_exceeded_error', wait_time, attempt, retry_attempts),
                           LINE_FOR_SHOW_LAST_ERROR)
    return wait_time


def get_video_data_by_video_id(video_id: int) -> ObjectData | None:  # pylint: disable=unused-argument
    """
    Get video data by video id
    """
    import glob

    files = glob.glob(os.path.join(get_video_data_path(), f"*_{video_id}.json"))
    file_path = files[0] if files else None
    if file_path is not None or os.path.isfile(str(file_path)):
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as file:
            try:
                data = json.load(file)
                object_data = ObjectData(**data)

                video_attribute = getattr(object_data, "video_attribute")
                if isinstance(video_attribute, dict):
                    object_data.video_attribute = AttributeObject(**video_attribute)  # pylint: disable=not-a-mapping

                return object_data
            except Exception as error2:  # pylint: disable=broad-except
                print(f"Error on loading file {file_name}: {error2}")
    return None


def get_video_data_by_message_id_reference(message_id_reference: int) -> ObjectData | None:
    """
    Get video data by message id reference
    """
    import glob

    files = glob.glob(os.path.join(get_video_data_path(), f"{message_id_reference}_*.json"))
    file_path = files[0] if files else None
    if file_path is not None or os.path.isfile(str(file_path)):
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as file:
            try:
                data = json.load(file)
                object_data = ObjectData(**data)

                video_attribute = getattr(object_data, "video_attribute")
                if isinstance(video_attribute, dict):
                    object_data.video_attribute = AttributeObject(**video_attribute)  # pylint: disable=not-a-mapping

                return object_data
            except Exception as error2:  # pylint: disable=broad-except
                print(f"Error on loading file {file_name}: {error2}")
    return None


async def fetch_all_messages(chat_id):
    """

    :param chat_id:
    :return:
    """
    from func.main import client

    all_messages = []

    async for message in client.iter_messages(chat_id):
        all_messages.append(message)

    return all_messages
