import os
import sys
import asyncio
import traceback
import mimetypes
from telethon.tl.types import DocumentAttributeVideo

# Add the 'func' directory to the system path to import custom modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'func'))

# Import necessary functions from custom modules
from func.config import load_config, get_system_language
from func.utils import check_folder_permissions, sanitize_filename, load_downloaded_files, acquire_lock, release_lock, \
    is_file_corrupted, save_downloaded_file, move_file, check_lock
from func.telegram_client import create_telegram_client, download_with_retry
from func.messages import get_message

# Get the directory where the script is located
root_dir = os.path.dirname(os.path.abspath(__file__))

# Check if a configuration file is provided as the first argument
if len(sys.argv) > 1:
    config_file_name = sys.argv[1]
else:
    config_file_name = 'tg-config.txt'

# Load the configuration
config_path = os.path.join(root_dir, config_file_name)
file_info_path = os.path.join(root_dir, 'file_info.csv')
config = load_config(config_path)

# Extract relevant information from the configuration
api_id = config.get('api_id')
api_hash = config.get('api_hash')
phone = config.get('phone')
download_folder = config.get('download_folder', os.path.join(root_dir, 'tg-video'))
completed_folder = config.get('completed_folder', os.path.join(root_dir, 'tg-video-completed'))
check_file = os.path.join(root_dir, config.get('check_file', './downloaded_files.txt'))
lock_file = os.path.join(root_dir, 'script.lock')
session_name = os.path.join(root_dir, config.get('session_name', 'session_name'))
max_simultaneous_file_to_download = config.get('max_simultaneous_file_to_download', 2)

# List of chat names or IDs to retrieve messages from
group_chats = config.get('group_chats', [])

# Determine the system language and load corresponding messages
language = get_system_language()
messages = get_message('', language)

# Create and check folders for downloads and completed files
check_folder_permissions(download_folder)
check_folder_permissions(completed_folder)

# Semaphore to limit the number of concurrent downloads
sem = asyncio.Semaphore(int(max_simultaneous_file_to_download))

async def download_with_limit(client, message, file_path, file_name, video_name, p_lock_file, status_messages):
    """Download a file with concurrency limit."""
    async with sem:
        # Send a status message before starting the download
        status_message = await client.send_message('me', f"🔔 Downloading video '{video_name}'...")
        status_messages.append(status_message)
        # Start downloading the file with retry logic
        await download_with_retry(client, message, file_path, status_message, file_name, video_name, p_lock_file, check_file, completed_folder)

async def delete_service_messages(client, all_messages):
    """Delete service messages from Telegram that match certain icons."""
    for message in all_messages:
        if message.text and any(icon in message.text for icon in ["⬇️", "‼️", "🔔"]):
            try:
                await client.delete_messages('me', [message.id])
                print(f"Deleted message with id: {message.id}")
            except Exception as delete_error:
                print(f"Failed to delete message with id: {message.id} - {delete_error}")

async def main():
    """Main function to manage the Telegram client and download files."""
    client = create_telegram_client(session_name, api_id, api_hash)

    try:
        await client.start(phone)
        print(messages['connection_success'])

        all_messages = []
        for chat in group_chats:
            print(f"Retrieving messages from {chat}: ...")
            async for message in client.iter_messages(chat, limit=1000):
                all_messages.append(message)

        if len(all_messages) == 0:
            print('No Messages found')
            await client.send_message('me', messages['no_message_found'])
            return

        # Delete previously created service messages
        await delete_service_messages(client, all_messages)

        # Extract video messages and map them to their positions
        video_messages = [msg for msg in all_messages if msg.document and any(isinstance(attr, DocumentAttributeVideo) for attr in msg.document.attributes)]
        video_positions = {msg.id: idx for idx, msg in enumerate(all_messages) if msg in video_messages}

        # Load the list of previously downloaded files
        downloaded_files = load_downloaded_files(check_file)
        status_messages = []

        tasks = []

        for message in video_messages:
            # Sanitize and get the video name from the message text
            video_name = sanitize_filename(message.text.split('\n')[0].strip()) if message.text else None

            # Extract the file name from the message's document attributes
            if len(message.media.document.attributes) > 1:
                file_name = sanitize_filename(message.media.document.attributes[1].file_name)
            else:
                file_name = None  # Handle the case where file_name is missing

            file_size = message.media.document.size

            # Get the next message if video_name is missing
            if not video_name:
                position = video_positions.get(message.id)
                if position is not None and 0 <= position - 1 < len(all_messages):
                    next_message = all_messages[position - 1]
                    if next_message.text and not any(symbol in next_message.text for symbol in ["⬇️", "‼️", "🔔", "✅ "]):
                        video_name = sanitize_filename(next_message.text.split('\n')[0].strip())

                if video_name is None and file_name is not None:
                    # Set video_name based on file_name if no valid video name was found
                    video_name = sanitize_filename(file_name.split('.')[0].strip())

                if video_name is None:
                    continue

            if file_name is None:
                file_name = f"{video_name}.mp4"

            if file_name is None:
                print("Error: file_name is None. Unable to determine the file path.")
                continue
            else:
                file_path = os.path.join(download_folder, file_name)

            # Check if the file already exists
            if os.path.exists(file_path):
                status_message = await client.send_message('me', messages['ready_to_move'].format(file_name))
                print(f"File ready to move: {file_name}")
                # Check if the file is corrupted before moving it
                if not is_file_corrupted(file_path, file_info_path):
                    save_downloaded_file(check_file, file_name)
                    mime_type, _ = mimetypes.guess_type(file_path)
                    extension = mimetypes.guess_extension(mime_type) if mime_type else ''
                    completed_file_path = os.path.join(completed_folder, video_name + extension)

                    if move_file(file_path, completed_file_path):
                        await status_message.edit(messages['download_complete'].format(video_name))
                    else:
                        await status_message.edit(messages['error_move_file'].format(video_name))
                else:
                    await status_message.edit(messages['corrupted_file'].format(file_name))
                continue

            # Skip already downloaded files
            if file_name in downloaded_files:
                print(f"File already downloaded: {file_name}")
                continue

            # Queue the download task with the limit on simultaneous downloads
            task = download_with_limit(client, message, file_path, file_name, video_name, lock_file, status_messages)
            tasks.append(task)

        # Execute all queued tasks concurrently
        await asyncio.gather(*tasks)

        # Delete status messages after downloads are completed
        for status_message in status_messages:
            await status_message.delete()

    finally:
        await client.disconnect()

if __name__ == '__main__':
    try:
        check_lock(lock_file)
        acquire_lock(lock_file)
        asyncio.run(main())
        release_lock(lock_file)
    except KeyboardInterrupt:
        print("Script interrupted manually.")
        release_lock(lock_file)
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
        release_lock(lock_file)
