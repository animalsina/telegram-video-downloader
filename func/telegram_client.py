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
from func.messages import get_message
from func.utils import update_file_info, release_lock, is_file_corrupted, remove_file_info, acquire_lock, \
    download_complete_action

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


async def update_download_message(message, percent, video_name, time_remaining_formatted):
    """Update the status message with the download progress and time remaining."""
    await message.edit(
        f"⬇️ Download '{video_name}': {percent:.2f}% complete.\nTime remaining: {time_remaining_formatted}")


def format_time(seconds):
    """Format time in seconds to a human-readable string like hh:mm:ss."""
    if seconds <= 0 or seconds == float('inf'):
        return "Calculating..."

    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def save_progress(file_path, progress):
    """Save the current download progress to a .progress file."""
    with open(f"{file_path}.progress", 'w', encoding='utf-8') as f:
        f.write(str(progress))


def load_progress(file_path):
    """Load and return the download progress from a .progress file."""
    try:
        with open(f"{file_path}.progress", 'r', encoding='utf-8') as f:
            return int(f.read())
    except ValueError:
        # Handle the case where the content cannot be converted to int
        return 0
    except FileNotFoundError:
        # Handle the case where the progress file doesn't exist
        return 0


async def download_with_retry(client, message, file_path, status_message, file_name, video_name, retry_attempts=5):
    """Download a file with retry attempts in case of failure."""
    configuration = load_configuration()
    attempt = 0
    last_update_time = time.time()
    last_current = 0
    file_size = message.media.document.size
    file_info_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'file_info.csv')
    temp_file_path = f"{file_path}.temp"
    progress_file_path = f"{file_path}.progress"
    messages = get_message('')
    lock_file = configuration.lock_file

    # Before starting, check if the progress/temp file exists; if not, remove the corresponding row from the CSV
    if os.path.exists(temp_file_path) is False or os.path.exists(progress_file_path) is False:
        remove_file_info(file_info_path, file_name)

    # Write initial file info to the CSV
    update_file_info(file_info_path, file_name, 'downloading', file_size)

    while attempt < retry_attempts:
        try:
            progress = load_progress(file_path) if os.path.exists(progress_file_path) else 0

            # If the temp file exists and is empty, delete both the temp and progress files and reset progress
            if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) == 0:
                os.remove(temp_file_path)
                os.remove(progress_file_path)
                progress = 0

            # Download the file with progress tracking
            with tqdm(total=file_size, initial=progress, desc=f"Downloading {message.id} - {file_name} - {video_name}",
                      unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                async def progress_callback(current, total):
                    nonlocal last_update_time
                    nonlocal last_current

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
                            await update_download_message(status_message, percent_complete, video_name,
                                                          time_remaining_formatted)
                            last_update_time = current_time
                            last_current = current

                        # Update the progress bar
                        pbar.update(current - pbar.n)
                        pbar.total = total
                        pbar.n = current

                        # Save the current progress
                        save_progress(file_path, current)

                # Download the media to the temp file using iter_download
                async with client.iter_download(message.media, offset=progress,
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
                os.rename(temp_file_path, file_path)
                os.remove(progress_file_path)
                print(f"Downloaded video to: {file_path}")

                if os.path.exists(file_path):
                    if not is_file_corrupted(file_path, file_info_path):
                        await download_complete_action(file_path, file_name, video_name, status_message)
                        update_file_info(file_info_path, file_name, 'completed', file_size)
                        return
                    else:
                        await status_message.edit(messages['corrupted_file'].format(file_name))
                        print(messages['corrupted_file'].format(file_name))
                return
            else:
                await status_message.edit(messages['file_mismatch_error'].format(video_name))
                os.remove(temp_file_path)
                os.remove(progress_file_path)
                raise Exception(f"File {video_name} size mismatch - I will delete temp file and retry.")

        except FloodWaitError as e:
            wait_time = e.seconds + 10  # Add a buffer time for safety
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")
            await status_message.edit(messages['rate_limit_exceeded_error'].format(wait_time))
            await asyncio.sleep(wait_time)
            attempt += 1

        except (OSError, IOError) as e:
            update_file_info(file_info_path, file_name, f'error: {str(e)}', file_size)
            await status_message.edit(messages['file_system_error'].format(str(e)))
            break

        except Exception as e:
            # Update the CSV with error information and stop the process
            update_file_info(file_info_path, file_name, f'error: {str(e)}', file_size)
            await status_message.edit(f"‼️ Unexpected error: {str(e)}")
            break

        finally:
            # Release the file lock after each attempt
            release_lock(lock_file)

    else:
        print("All retry attempts failed.")
        await status_message.edit(messages['all_attempts_failed'].format(video_name))
        release_lock(lock_file)
