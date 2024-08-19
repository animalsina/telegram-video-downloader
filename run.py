import os
import sys
import asyncio
import traceback
import mimetypes
from telethon.tl.types import DocumentAttributeVideo

sys.path.append(os.path.join(os.path.dirname(__file__), 'func'))

from func.config import load_config, get_system_language
from func.utils import check_folder_permissions, sanitize_filename, load_downloaded_files, save_downloaded_file, acquire_lock, release_lock, is_file_corrupted, move_file
from func.telegram_client import create_telegram_client, download_with_retry
from func.messages import get_message

# Get the directory where the script is located
root_dir = os.path.dirname(os.path.abspath(__file__))

# Load the configuration
config_path = os.path.join(root_dir, 'tg-config.txt')
file_info_path = os.path.join(root_dir, 'file_info.csv')
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

async def main():
    client = create_telegram_client(session_name, api_id, api_hash)

    try:
        print(messages['start_connection'])
        await client.start(phone)
        print(messages['connection_success'])

        all_messages = []
        print(messages['retrieving_messages'])
        async for message in client.iter_messages('me', limit=1000):
            all_messages.append(message)

        # Extract video messages and map them to their positions
        video_messages = [msg for msg in all_messages if msg.document and any(isinstance(attr, DocumentAttributeVideo) for attr in msg.document.attributes)]
        video_positions = {msg.id: idx for idx, msg in enumerate(all_messages) if msg in video_messages}

        downloaded_files = load_downloaded_files(check_file)
        status_messages = []

        for message in video_messages:
            video_name = sanitize_filename(message.text.split('\n')[0].strip()) if message.text else None
            if len(message.media.document.attributes) > 1:
                file_name = message.media.document.attributes[1].file_name
            else:
                file_name = None  # O un valore di default o gestisci l'assenza del file_name

            file_size = message.media.document.size

            # Get the next message if video_name is missing
            if not video_name:
                position = video_positions.get(message.id)
                if position is not None and 0 <= position - 1 < len(all_messages):
                    next_message = all_messages[position - 1]
                    if next_message.text:
                        video_name = sanitize_filename(next_message.text.split('\n')[0].strip())
                else:
                    print(f"Index {position - 1} is out of range for all_messages")
                if not video_name:
                    # Imposta video_name basato su file_name se non è stato trovato un nome video valido
                    video_name = file_name.split('.')[0]
                    print(f"Cannot get name for the message: {message.id}")

            if file_name is None:
                file_name = f"{video_name}.mp4"

            if file_name in downloaded_files:
                print(f"File already downloaded: {file_name}")
                continue

            if file_name is None:
                print("Errore: file_name è None. Impossibile determinare il percorso del file.")
            else:
                file_path = os.path.join(download_folder, file_name)

            status_message = await client.send_message('me', f"Downloading video '{video_name}'...")
            status_messages.append(status_message)

            await download_with_retry(client, message, file_path, status_message, file_name, video_name, messages, lock_file)

            if not is_file_corrupted(file_path, file_info_path):
                if(os.path.exists(file_path)):
                    save_downloaded_file(check_file, file_name)
                    mime_type, _ = mimetypes.guess_type(file_path)
                    extension = mimetypes.guess_extension(mime_type) if mime_type else ''
                    completed_file_path = os.path.join(completed_folder, video_name + extension)

                    if move_file(file_path, completed_file_path, messages):
                        await status_message.edit(messages['download_complete'].format(file_name))
                    else:
                        await status_message.edit(messages['error_move_file'].format(file_name))
                else:
                    await status_message.edit(messages['not_found_file'].format(file_name))
            else:
                await status_message.edit(messages['corrupted_file'].format(file_name))

        for status_message in status_messages:
            await status_message.delete()

    finally:
        await client.disconnect()
        release_lock(lock_file)

if __name__ == '__main__':
    try:
        acquire_lock(lock_file, messages)
        asyncio.run(main())
        release_lock(lock_file)
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        release_lock(lock_file)
