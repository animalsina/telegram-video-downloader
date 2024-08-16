from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from tqdm import tqdm
import os
import shutil
import traceback
import sys
import re
import time
import locale
from telethon.errors import FloodWaitError
import asyncio

# Load the configuration from the file
def load_config(file_path):
    config = {}
    with open(file_path, 'r') as f:
        for line in f:
            key, value = line.strip().split('=', 1)
            config[key] = value
    # Convert min_valid_file_size_mb to bytes
    if 'min_valid_file_size_mb' in config:
        try:
            min_size_mb = float(config['min_valid_file_size_mb'])
            config['min_valid_file_size'] = min_size_mb * 1024 * 1024  # Convert MB to bytes
        except ValueError:
            config['min_valid_file_size'] = 0
    else:
        config['min_valid_file_size'] = 0
    return config

# Check folder permissions
def check_folder_permissions(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    if not os.path.isdir(folder_path):
        raise PermissionError(f"{folder_path} is not a directory.")
    if not os.access(folder_path, os.W_OK):
        raise PermissionError(f"Permission denied: {folder_path}")

# Sanitize filename to remove invalid characters
def sanitize_filename(filename):
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '', filename)  # Remove invalid characters for Windows
    sanitized_name = re.sub(r'[^\w\s.-]', '', sanitized_name)  # Remove special characters (except alphanumeric, spaces, dots, hyphens, underscores)
    return sanitized_name.strip()

# Load the language configuration from the system
def get_system_language():
    lang, _ = locale.getdefaultlocale()
    if lang.startswith('it'):
        return 'it'
    return 'en'

# Get the localized message based on the language configuration
def get_message(key, language):
    messages = {
        'en': {
            'start_connection': "Starting connection to the client...",
            'connection_success': "Connection successful.",
            'retrieving_messages': "Retrieving messages...",
            'found_videos': "Found {} videos.",
            'error_message': "Error message deleted.",
            'starting_download': "Starting download: {}",
            'download_started': "⬇️ Downloading: {}%",
            'corrupted_file': "The file '{}' is corrupted. Re-downloading...",
            'download_complete': "✅ Download completed and moved: {}\nCompleted",
            'error_move_file': "❌ Error moving file: {}",
            'error_download': "❌ Error downloading video '{}': {}",
            'permission_error': "Permission error: {}",
            'script_running': "Script already running."
        },
        'it': {
            'start_connection': "Inizio connessione al client...",
            'connection_success': "Connessione avvenuta con successo.",
            'retrieving_messages': "Recupero dei messaggi...",
            'found_videos': "Trovati {} video.",
            'error_message': "Messaggio di errore eliminato.",
            'starting_download': "Inizio download: {}",
            'download_started': "⬇️ Scaricando: {}%",
            'corrupted_file': "Il file '{}' è corrotto. Riscaricando...",
            'download_complete': "✅ Download completato e spostato: {}\nCompletato",
            'error_move_file': "❌ Errore durante lo spostamento del file: {}",
            'error_download': "❌ Errore durante il download del video '{}': {}",
            'permission_error': "Errore di permesso: {}",
            'script_running': "Script già in esecuzione."
        }
    }
    return messages.get(language, messages['en'])  # Default to English if the language is not supported

# Get the directory where the script is located
root_dir = os.path.dirname(os.path.abspath(__file__))

# Load the configuration
config_path = os.path.join(root_dir, 'tg-config.txt')
config = load_config(config_path)

api_id = config.get('api_id')
api_hash = config.get('api_hash')
phone = config.get('phone')
download_folder = config.get('download_folder', 'tg-video')
completed_folder = config.get('completed_folder', 'tg-video-completed')
check_file = os.path.join(root_dir, config.get('check_file', 'downloaded_files.txt'))
lock_file = os.path.join(root_dir, 'script.lock')
session_name = os.path.join(root_dir, config.get('session_name', 'session_name'))
min_valid_file_size = config.get('min_valid_file_size', 100)

# Determine the system language and load messages
language = get_system_language()
messages = get_message('', language)

# Create and check folders
check_folder_permissions(download_folder)
check_folder_permissions(completed_folder)

# Load the list of already downloaded files
def load_downloaded_files():
    if os.path.exists(check_file):
        with open(check_file, 'r') as f:
            return set(line.strip() for line in f)
    return set()

# Save a file in the list of downloaded files
def save_downloaded_file(file_name):
    with open(check_file, 'a') as f:
        f.write(file_name + '\n')

# Handle the lock file
def acquire_lock():
    if os.path.exists(lock_file):
        print(messages['script_running'])
        sys.exit()
    open(lock_file, 'w').close()

def release_lock():
    if os.path.exists(lock_file):
        os.remove(lock_file)

# Move a file handling cross-device links
def move_file(src, dest):
    try:
        shutil.move(src, dest)
        print(f"Video saved and moved to: {dest}")
        return True
    except Exception as e:
        print(messages['error_move_file'].format(os.path.basename(src)))
        return False

# Check if a file is corrupted or incomplete
def is_file_corrupted(file_path, min_valid_size):
    if os.path.exists(file_path):
        actual_size = os.path.getsize(file_path)
        if actual_size < min_valid_size:
            return True
    return False

# Get and sanitize video name
def get_video_name(message, all_messages):
    if message.text:
        return sanitize_filename(message.text.split('\n')[0].strip())
    
    try:
        current_index = all_messages.index(message)
    except ValueError:
        print(messages['error_message'])
        return None

    if current_index > 0:
        prev_message = all_messages[current_index - 1]
        if prev_message.text:
            video_name = sanitize_filename(prev_message.text.split('\n')[0].strip())
            return video_name
        else:
            print(messages['error_message'])
            return None
    else:
        print(messages['error_message'])
        return None

# Create a Telegram client
client = TelegramClient(session_name, api_id, api_hash)

# Function to update download message with progress every 5 seconds
async def update_download_message(message, percent, file_name):
    await message.edit(f"⬇️ Scaricando '{file_name}': {percent:.2f}% completato")

# Function to handle download with retry
async def download_with_retry(client, message, file_path, status_message, file_name, retry_attempts=5):
    attempt = 0
    last_update_time = time.time()  # Initialize last_update_time here

    while attempt < retry_attempts:
        try:
            with tqdm(total=100, desc=f"Downloading {message.id}", unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                async def progress_callback(current, total):
                    nonlocal last_update_time
                    if total is not None:
                        percent_complete = (current / total) * 100
                        current_time = time.time()
                        if current_time - last_update_time >= 5:  # Update every 5 seconds
                            await update_download_message(status_message, percent_complete, file_name)
                            last_update_time = current_time
                        pbar.update(current - pbar.n)
                        pbar.total = total
                        pbar.n = current

                await client.download_media(message, file_path, progress_callback=progress_callback)
            print(f"Downloaded video to: {file_path}")
            return
        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")
            await asyncio.sleep(wait_time)
            attempt += 1
        except Exception as e:
            print(f"Error downloading video: {str(e)}")
            break

async def main():
    try:
        print(messages['start_connection'])
        await client.start(phone)
        print(messages['connection_success'])

        # Retrieve all messages from "Saved Messages"
        all_messages = []
        print(messages['retrieving_messages'])
        async for message in client.iter_messages('me', limit=100):
            all_messages.append(message)
        
        # Filter only videos
        messages_list = [msg for msg in all_messages if msg.document and any(isinstance(attr, DocumentAttributeVideo) for attr in msg.document.attributes)]
        print(messages['found_videos'].format(len(messages_list)))

        # Clear old error messages if there are new videos to download
        if messages_list:
            async for old_message in client.iter_messages('me', from_user='me'):
                if "❌" in old_message.text:
                    await old_message.delete()
                    print(messages['error_message'])

        downloaded_files = load_downloaded_files()

        for message in tqdm(messages_list, desc="Downloading Videos"):
            video_name = get_video_name(message, all_messages)

            if not video_name:
                print(f"Cannot get name for the video in message {message.id}. The video will be ignored.")
                continue

            file_path = os.path.join(download_folder, f"{video_name}.mp4")
            completed_file_path = os.path.join(completed_folder, f"{video_name}.mp4")

            status_message = await client.send_message('me', messages['starting_download'].format(video_name))

            if video_name in downloaded_files:
                if os.path.exists(completed_file_path):
                    await status_message.edit(messages['download_complete'].format(video_name))
                    await status_message.delete()
                    continue
                else:
                    await status_message.edit(f"⏳ The video '{video_name}' has been downloaded but not moved. Retrying move...")

            if os.path.exists(file_path):
                if is_file_corrupted(file_path, min_valid_file_size):
                    print(messages['corrupted_file'].format(file_path))
                    os.remove(file_path)
                    await status_message.edit(messages['corrupted_file'].format(video_name))

                    # Re-download the video
                    try:
                        await download_with_retry(client, message, file_path, status_message, video_name)
                        print(f"Re-downloaded video to: {file_path}")
                    except Exception as e:
                        print(messages['error_download'].format(video_name, str(e)))
                        await status_message.edit(messages['error_download'].format(video_name, str(e)))
                        continue

            try:
                # Start download
                await download_with_retry(client, message, file_path, status_message, video_name)
                print(f"Downloaded video to: {file_path}")

                if move_file(file_path, completed_file_path):
                    save_downloaded_file(video_name)
                    await status_message.edit(messages['download_complete'].format(video_name))
                else:
                    await status_message.edit(messages['error_move_file'].format(video_name))

            except Exception as e:
                print(messages['error_download'].format('', str(e)))
                await status_message.edit(messages['error_download'].format('', str(e)))

            if '✅' in status_message.text:
                await status_message.delete()

    except PermissionError as e:
        print(messages['permission_error'].format(e))
        release_lock()
    except Exception as e:
        print(messages['error_download'].format('', str(e)))
        traceback.print_exc()
        release_lock()
    finally:
        release_lock()

if __name__ == "__main__":
    try:
        acquire_lock()
        with client:
            client.loop.run_until_complete(main())
    except Exception as e:
        print(messages['error_download'].format('', str(e)))
        traceback.print_exc()
        release_lock()

