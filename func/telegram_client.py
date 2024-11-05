"""
Module for interacting with Telegram API to download files with progress tracking and retry logic.
"""
import time
import os
import asyncio
import collections

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from tqdm import tqdm

from func.config import load_configuration
from func.messages import t
from func.utils import release_lock, is_file_corrupted, acquire_lock, \
    download_complete_action, add_line_to_text, LINE_FOR_INFO_DATA, LINE_FOR_SHOW_LAST_ERROR

# Buffer to store speed data samples
speed_samples = collections.deque(maxlen=20)  # Keep only the last 100 samples

def calculate_download_speed(current, time_elapsed, last_current):
    """Calculate download speed."""
    if time_elapsed <= 0:
        return 0
    return (current - last_current) / time_elapsed


def create_telegram_client(session_name, api_id, api_hash):
    """Create and return a new TelegramClient."""
    return TelegramClient(session_name, api_id, api_hash)


async def update_download_message(reference_message, percent, time_remaining_formatted):
    """Update the status message with the download progress and time remaining."""
    await add_line_to_text(reference_message,
                           f"⬇️ Download: {percent:.2f}% - {time_remaining_formatted}",
                           LINE_FOR_INFO_DATA)


def format_time(seconds):
    """Format time in seconds to a human-readable string like hh:mm:ss."""
    if seconds <= 0 or seconds == float('inf'):
        return "Calculating..."

    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


async def progress_tracking(
        progress, file_size, video, last_update_time, temp_file_path, last_current
):
    """
    Track the download progress and update the status message.
    """
    from run import root_dir
    from main import client, configuration

    configuration = load_configuration()

    with tqdm(total=file_size, initial=progress,
              desc=f"Downloading {video.video_id} - {video.file_name} -"
                   f" {video.video_name_cleaned}",
              unit='B', unit_scale=True, unit_divisor=1024) as pbar:
        async def progress_callback(current, total):
            nonlocal last_current
            nonlocal last_update_time

            if os.path.exists(os.path.join(root_dir, '.stop')):
                os.remove(os.path.join(root_dir, '.stop'))
                raise Exception('Stop forzato del download') # pylint: disable=broad-exception-raised

            if total is not None:
                percent_complete = (current / total) * 100
                current_time = time.time()

                # Calculate time elapsed
                time_elapsed = current_time - last_update_time

                # Calculate download speed
                download_speed = calculate_download_speed(current, time_elapsed, last_current)

                # Add the current speed to the speed sample buffer
                speed_samples.append(download_speed)

                # Calculate average speed for a more accurate estimate
                average_speed = (sum(speed_samples) / len(speed_samples)
                                 if speed_samples else 0)
                time_remaining = ((total - current) / average_speed
                                  if average_speed > 0 else float('inf'))

                # Update the status message every 3 seconds
                if current_time - last_update_time >= 3:
                    acquire_lock(configuration.lock_file)
                    time_remaining_formatted = format_time(time_remaining)
                    await update_download_message(video.reference_message,
                                                  percent_complete,
                                                  time_remaining_formatted)
                    last_update_time = current_time
                    last_current = current

                # Update the progress bar
                pbar.update(current - pbar.n)
                pbar.total = total
                pbar.n = current

        # Download the media to the temp file using iter_download
        async with client.iter_download(video.video_media, offset=progress,
                                        request_size=64 * 1024) as download_iter:
            with open(temp_file_path, 'ab') as f:
                async for chunk in download_iter:
                    f.write(chunk)
                    await progress_callback(f.tell(), file_size)

async def download_with_retry(client, video, retry_attempts=5):
    """Download a file with retry attempts in case of failure."""
    from run import PERSONAL_CHAT_ID
    from main import configuration

    # Here checks for video data, because if video is stored during the iteration, it will expire
    video_message_data = await client.get_messages(PERSONAL_CHAT_ID, ids=video.message_id_reference)
    if video.is_forward_chat_protected is not True:
        video.video_media = video_message_data.media
    else:
        video_data = await client.get_messages(video.chat_name, ids=video.video_id)
        video.video_media = video_data.media

    attempt = 0
    progress = 0
    last_current = 0
    last_update_time = time.time()
    file_size = video.video_media.document.size
    temp_file_path = f"{video.file_path}.temp"

    while attempt < retry_attempts:
        try:
            if os.path.exists(temp_file_path):
                progress = os.path.getsize(temp_file_path)

            # Download the file with progress tracking
            await progress_tracking(
                progress, file_size, video, last_update_time, temp_file_path, last_current
            )

            # Wait 3 seconds before to get temp file size
            await asyncio.sleep(3)
            temp_file_size = os.path.getsize(temp_file_path)

            tolerance = 0  # Tolerance in bytes, adjust as needed

            # Check if the temp file is complete and then move it to the final path
            if abs(temp_file_size - file_size) <= tolerance:
                os.rename(temp_file_path, video.file_path)
                print(f"Downloaded video to: {video.file_path}")

                if os.path.exists(video.file_path):
                    if not is_file_corrupted(video.file_path, file_size):
                        await download_complete_action(video)
                        return
                    await add_line_to_text(video.reference_message,
                                           t('corrupted_file', video.file_name),
                                           LINE_FOR_SHOW_LAST_ERROR)
                    print(t('corrupted_file', video.file_name))
                return
            await add_line_to_text(video.reference_message,
                                   t('file_mismatch_error', video.video_name),
                                   LINE_FOR_SHOW_LAST_ERROR)
            os.remove(temp_file_path)
            raise Exception(  # pylint: disable=broad-exception-raised
                f"File {video.video_name} size mismatch - I will delete temp file and retry."
            )

        except FloodWaitError as e:
            wait_time = e.seconds + 10  # Add a buffer time for safety
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")
            await add_line_to_text(video.reference_message,
                                   t('rate_limit_exceeded_error', wait_time),
                                   LINE_FOR_SHOW_LAST_ERROR)
            await asyncio.sleep(wait_time)
            attempt += 1

        except (OSError, IOError) as e:
            print(f"File system error: {str(e)}")
            await add_line_to_text(video.reference_message, t('file_system_error', str(e)),
                                   LINE_FOR_SHOW_LAST_ERROR)
            break

        except Exception as error:  # pylint: disable=broad-exception-caught
            print(f"Unexpected error: {str(error)}")
            await add_line_to_text(video.reference_message, f"‼️ Unexpected error: {str(error)}",
                                   LINE_FOR_SHOW_LAST_ERROR)
            break

        finally:
            # Release the file lock after each attempt
            release_lock(configuration.lock_file)

    else:
        print("All retry attempts failed.")
        release_lock(configuration.lock_file)
