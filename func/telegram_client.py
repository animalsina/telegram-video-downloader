from telethon import TelegramClient
from telethon.errors import FloodWaitError
from tqdm import tqdm
import mimetypes
import time
import os
import asyncio
import csv
import collections

from func.utils import update_file_info, release_lock, is_file_corrupted, save_downloaded_file, move_file, remove_file_info

# Buffer to store speed data samples
speed_samples = collections.deque(maxlen=100)  # Keep only the last 100 samples

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
    await message.edit(f"⬇️ Download '{video_name}': {percent:.2f}% complete.\nTime remaining: {time_remaining_formatted}")

def format_time(seconds):
    """Format time in seconds to a human-readable string like hh:mm:ss."""
    if seconds <= 0 or seconds == float('inf'):
        return "Calculating..."

    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

def save_progress(file_path, progress):
    """Save the current download progress to a .progress file."""
    with open(f"{file_path}.progress", 'w') as f:
        f.write(str(progress))

def load_progress(file_path):
    """Load and return the download progress from a .progress file."""
    try:
        with open(f"{file_path}.progress", 'r') as f:
            return int(f.read())
    except ValueError:
        # Handle the case where the content cannot be converted to int
        return 0
    except FileNotFoundError:
        # Handle the case where the progress file doesn't exist
        return 0

async def download_with_retry(client, message, file_path, status_message, file_name, video_name, messages, lock_file, check_file, completed_folder, retry_attempts=5):
    """Download a file with retry attempts in case of failure."""
    attempt = 0
    last_update_time = time.time()
    last_current = 0
    file_size = message.media.document.size
    file_info_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'file_info.csv')
    temp_file_path = f"{file_path}.temp"
    progress_file_path = f"{file_path}.progress"

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
            with tqdm(total=file_size, initial=progress, desc=f"Downloading {message.id} - {file_name} - {video_name}", unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                async def progress_callback(current, total):
                    nonlocal last_update_time
                    nonlocal last_current
                    file_size = message.file.size
                    progress = load_progress(file_path)

                    if total is not None:
                        percent_complete = (current / total) * 100
                        current_time = time.time()

                        # Calculate time elapsed
                        time_elapsed = current_time - last_update_time

                        # Calculate download speed
                        download_speed = calculate_download_speed(current, last_current, time_elapsed)

                        # Estimate time remaining
                        if download_speed > 0:
                            time_remaining = (total - current) / download_speed
                        else:
                            time_remaining = float('inf')

                        # Add the current speed to the speed sample buffer
                        speed_samples.append(download_speed)

                        # Calculate average speed for a more accurate estimate
                        if speed_samples:
                            average_speed = sum(speed_samples) / len(speed_samples)
                            time_remaining = (total - current) / average_speed if average_speed > 0 else float('inf')
                        else:
                            average_speed = 0

                        # Update the status message every 3 seconds
                        if current_time - last_update_time >= 3:
                            time_remaining_formatted = format_time(time_remaining)
                            await update_download_message(status_message, percent_complete, video_name, time_remaining_formatted)
                            last_update_time = current_time
                            last_current = current

                        # Update the progress bar
                        pbar.update(current - pbar.n)
                        pbar.total = total
                        pbar.n = current

                        # Save the current progress
                        save_progress(file_path, current)

                # Download the media to the temp file using iter_download
                async with client.iter_download(message.media, offset=progress, request_size=64 * 1024) as download_iter:
                    with open(temp_file_path, 'ab') as f:
                        async for chunk in download_iter:
                            f.write(chunk)
                            await progress_callback(f.tell(), file_size)

            temp_file_size = os.path.getsize(temp_file_path)

            tolerance = 5  # Tolerance in bytes, adjust as needed

            # Check if the temp file is complete and then move it to the final path
            if abs(temp_file_size - file_size) <= tolerance:
                os.rename(temp_file_path, file_path)
                os.remove(progress_file_path)
                print(f"Downloaded video to: {file_path}")
                status_message = await client.send_message('me', f"🔔 File ready to move: {file_name}")
                print(f"File ready to move: {file_name}")

                if(os.path.exists(file_path)):
                    if not is_file_corrupted(file_path, file_info_path):
                        save_downloaded_file(check_file, file_name)
                        mime_type, _ = mimetypes.guess_type(file_path)
                        extension = mimetypes.guess_extension(mime_type) if mime_type else ''
                        completed_file_path = os.path.join(completed_folder, video_name + extension)

                        if move_file(file_path, completed_file_path, messages):
                            await status_message.edit(messages['download_complete'].format(video_name))
                        else:
                            await status_message.edit(messages['error_move_file'].format(video_name))
                    else:
                        await status_message.edit(messages['corrupted_file'].format(file_name))
                    update_file_info(file_info_path, file_name, 'completed', file_size)
                return
            else:
                await status_message.edit(f"‼️ File {video_name} size mismatch - I will delete temp file and retry.")
                os.remove(temp_file_path)
                os.remove(progress_file_path)
                raise Exception(f"File {video_name} size mismatch - I will delete temp file and retry.")

        except FloodWaitError as e:
            wait_time = e.seconds + 10  # Add a buffer time for safety
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")
            await status_message.edit(f"‼️ Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")
            await asyncio.sleep(wait_time)
            attempt += 1

        except Exception as e:
            # Update the CSV with error information and stop the process
            update_file_info(file_info_path, file_name, f'error: {str(e)}', file_size)
            await status_message.edit(f"‼️ Error: {str(e)}")
            break

        finally:
            # Release the file lock after each attempt
            release_lock(lock_file)

    else:
        print("All retry attempts failed.")
        await status_message.edit(f"‼️ All retry attempts failed - {video_name} - retry on next check.")
        release_lock(lock_file)
