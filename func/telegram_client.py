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
    download_complete_action, add_line_to_text, line_for_info_data, line_for_show_last_error

# Buffer to store speed data samples
speed_samples = collections.deque(maxlen=20)  # Keep only the last 100 samples

def calculate_download_speed(current, last_current, time_elapsed):
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
                           f"⬇️ Download: {percent:.2f}% - {time_remaining_formatted}", line_for_info_data)


def format_time(seconds):
    """Format time in seconds to a human-readable string like hh:mm:ss."""
    if seconds <= 0 or seconds == float('inf'):
        return "Calculating..."

    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

async def download_with_retry(client, video, retry_attempts=5):
    """Download a file with retry attempts in case of failure."""
    from run import root_dir, personal_chat_id

    # Here checks for video data, because if video is stored during the iteration, it will expire
    video_message_data = await client.get_messages(personal_chat_id, ids=video.message_id_reference)
    video.video_media = video_message_data.media

    configuration = load_configuration()
    attempt = 0
    last_update_time = time.time()
    last_current = 0
    file_size = video.video_media.document.size
    temp_file_path = f"{video.file_path}.temp"
    lock_file = configuration.lock_file
    progress = 0

    while attempt < retry_attempts:
        try:
            if os.path.exists(temp_file_path):
                progress = os.path.getsize(temp_file_path)

            # Download the file with progress tracking
            with tqdm(total=file_size, initial=progress,
                      desc=f"Downloading {video.video_id} - {video.file_name} - {video.video_name_cleaned}",
                      unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                async def progress_callback(current, total):
                    nonlocal last_update_time
                    nonlocal last_current

                    if os.path.exists(os.path.join(root_dir, '.stop')):
                        os.remove(os.path.join(root_dir, '.stop'))
                        raise Exception('Stop forzato del download')

                    if total is not None:
                        percent_complete = (current / total) * 100
                        current_time = time.time()

                        # Calculate time elapsed
                        time_elapsed = current_time - last_update_time

                        # Calculate download speed
                        download_speed = calculate_download_speed(current, last_current, time_elapsed)

                        # Add the current speed to the speed sample buffer
                        speed_samples.append(download_speed)

                        # Calculate average speed for a more accurate estimate
                        average_speed = sum(speed_samples) / len(speed_samples) if speed_samples else 0
                        time_remaining = (total - current) / average_speed if average_speed > 0 else float('inf')

                        # Update the status message every 3 seconds
                        if current_time - last_update_time >= 3:
                            acquire_lock(lock_file)
                            time_remaining_formatted = format_time(time_remaining)
                            await update_download_message(video.reference_message, percent_complete,
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
                    else:
                        await add_line_to_text(video.reference_message,
                                               t('corrupted_file', video.file_name), line_for_show_last_error)
                        print(t('corrupted_file', video.file_name))
                return
            else:
                await add_line_to_text(video.reference_message,
                                       t('file_mismatch_error', video.video_name), line_for_show_last_error)
                os.remove(temp_file_path)
                raise Exception(f"File {video.video_name} size mismatch - I will delete temp file and retry.")

        except FloodWaitError as e:
            wait_time = e.seconds + 10  # Add a buffer time for safety
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")
            await add_line_to_text(video.reference_message, t('rate_limit_exceeded_error', wait_time), line_for_show_last_error)
            await asyncio.sleep(wait_time)
            attempt += 1

        except (OSError, IOError) as e:
            await add_line_to_text(video.reference_message, t('file_system_error', str(e)), line_for_show_last_error)
            break

        except Exception as e:
            await add_line_to_text(video.reference_message, f"‼️ Unexpected error: {str(e)}", line_for_show_last_error)
            break

        finally:
            # Release the file lock after each attempt
            release_lock(lock_file)

    else:
        print("All retry attempts failed.")
        release_lock(lock_file)
