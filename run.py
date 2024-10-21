import os
import sys
import asyncio
import traceback
from pathlib import Path

from telethon.tl.types import DocumentAttributeVideo
from telethon.tl.types import DocumentAttributeFilename

from func.config import load_configuration
from func.rules import load_rules, apply_rules

# Add the 'func' directory to the system path to import custom modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'func'))

# Import necessary functions from custom modules
from func.utils import sanitize_filename, load_downloaded_files, acquire_lock, release_lock, is_file_corrupted, \
    check_lock, is_video_file, download_complete_action
from func.telegram_client import create_telegram_client, download_with_retry
from func.messages import get_message

root_dir = os.path.dirname(os.path.abspath(__file__))

configuration = load_configuration()
sem = asyncio.Semaphore(configuration.max_simultaneous_file_to_download)

async def download_with_limit(client, message, file_path, file_name, video_name):
    """Download a file with concurrency limit."""
    msgs = get_message('')

    # Inizializza il semaforo per gestire i download simultanei
    async with sem:
        # Send a status message before starting the download
        status_message = await client.send_message('me', msgs['download_video'].format(video_name))
        # Start downloading the file with retry logic
        await download_with_retry(client, message, file_path, status_message, file_name, video_name)


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

    messages_el = configuration.messages
    client = create_telegram_client(configuration.session_name, configuration.api_id, configuration.api_hash)

    try:
        await client.start(configuration.phone)
        print(messages_el['connection_success'])

        all_messages = []
        replies_msg = []
        for chat in configuration.group_chats:
            print(messages_el['retrieving_messages'].format(chat))
            async for message in client.iter_messages(chat, limit=1000):
                if message.reply_to_msg_id:
                    replies_msg.append(message)
                all_messages.append(message)

        if len(all_messages) == 0:
            print('No Messages found')
            await client.send_message('me', messages_el['no_message_found'])
            return

        # Delete previously created service messages
        await delete_service_messages(client, all_messages)

        video_messages = []

        for message in all_messages:
            if message.document:
                if any(isinstance(attr, DocumentAttributeVideo) for attr in message.document.attributes):
                    video_messages.append(message)
                else:
                    # Check if the document is a video based on its extension
                    file_name = None
                    for attr in message.media.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            file_name = sanitize_filename(attr.file_name)
                            break
                    if file_name and is_video_file(file_name):
                        video_messages.append(message)

        # Load the list of previously downloaded files
        downloaded_files = load_downloaded_files(configuration.check_file)

        tasks = []

        video_messages.reverse()
        video_messages.sort(key=lambda msg: not msg.pinned)

        for message in video_messages:
            video_name = None
            file_name = None

            # Check for reply message and set like video_name
            if not video_name and len(replies_msg) > 0:
                for replyMsg in replies_msg:
                    if replyMsg.reply_to_msg_id == message.id:
                        message_title = sanitize_filename(replyMsg.text.split('\n')[0].strip())
                        if message_title and not any(
                                icon in message_title for icon in ["⬇️", "‼️", "🔔", "❌", "✅", "🗜️"]):
                            video_name = message_title

            # Cerca il nome del file dal messaggio corrente
            if video_name is None:
                full_msg_rows = message.text.split('\n')
                if len(full_msg_rows) > 0:
                    msg1 = full_msg_rows[0].strip()
                else:
                    msg1 = ''

                if len(full_msg_rows) > 1:
                    msg2 = full_msg_rows[1].strip()
                else:
                    msg2 = ''

                if len(full_msg_rows) > 2:
                    msg3 = full_msg_rows[2].strip()
                else:
                    msg3 = ''

                video_name = sanitize_filename(msg1 + msg2 + msg3) if message.text else None

            # Codice esistente per trovare il file_name
            for attr in message.media.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    file_name = sanitize_filename(attr.file_name)
                    break

            # If video_name is None and file_name is not none then set file_name to video_name
            if video_name is None and file_name is not None:
                # Set video_name based on file_name if no valid video name was found
                video_name = sanitize_filename(file_name.rsplit('.', 1)[0].strip())

            # If video_name is empty send an alert message to personal chat
            if video_name is None:
                await client.send_message(
                    message.peer_id,
                    messages_el['empty_reference_specify_name'],
                    reply_to=message.id
                )
                continue

            video_name = apply_rules('translate', video_name)

            if file_name is None:
                file_name = f"{video_name}.mp4"

            if file_name is None:
                print("Error: file_name is None. Unable to determine the file path.")
                continue
            else:
                file_path = os.path.join(configuration.download_folder, file_name)

            if file_name is None:
                break

            # Check if the file already exists
            if os.path.exists(file_path):
                status_message = await client.send_message('me', messages_el['ready_to_move'].format(file_name))
                print(messages['ready_to_move'].format(file_name))

                # Check if the file is corrupted before moving it
                if not is_file_corrupted(file_path, configuration.file_info_path):
                    await download_complete_action(file_path, file_name, video_name, status_message)
                else:
                    await status_message.edit(messages_el['corrupted_file'].format(file_name))
                    print(messages_el['corrupted_file'].format(file_name))
                    os.remove(file_path)
                continue

            # Skip already downloaded files
            if file_name in downloaded_files:
                print(messages_el['already_downloaded'].format(file_name))
                continue

            # Queue the download task with the limit on simultaneous downloads
            task = download_with_limit(client, message, file_path, file_name, video_name)
            tasks.append(task)

        # Execute all queued tasks concurrently
        await asyncio.gather(*tasks)

    finally:
        await client.disconnect()


if __name__ == '__main__':
    load_rules(Path(root_dir))
    messages = configuration.messages
    lock_file = configuration.lock_file
    if configuration.disabled:
        print("Disabled")
        exit(0)
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
