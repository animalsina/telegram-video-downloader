import os
import re
import sys
import asyncio
import traceback
import pickle
from pathlib import Path

import telethon
from telethon.tl.types import DocumentAttributeVideo
from telethon.tl.types import DocumentAttributeFilename

from func.config import load_configuration
from func.rules import load_rules, apply_rules

# Add the 'func' directory to the system path to import custom modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'func'))

# Import necessary functions from custom modules
from func.utils import sanitize_filename, acquire_lock, release_lock, is_file_corrupted, \
    check_lock, is_video_file, download_complete_action, add_line_to_text, save_pickle_data, line_for_info_data, \
    default_video_message
from func.telegram_client import create_telegram_client, download_with_retry
from func.messages import get_message

root_dir = os.path.dirname(os.path.abspath(__file__))

configuration = load_configuration()
sem = asyncio.Semaphore(configuration.max_simultaneous_file_to_download)

client = create_telegram_client(configuration.session_name, configuration.api_id, configuration.api_hash)
all_messages = []
replies_msg = []
# Load the list of previously downloaded files

tasks = []

async def download_with_limit(video):
    """Download a file with concurrency limit."""
    msgs = get_message('')

    # Inizializza il semaforo per gestire i download simultanei
    async with sem:
        # Send a status message before starting the download
        await add_line_to_text(video.reference_message, msgs['download_video'], line_for_info_data)

        # Start downloading the file with retry logic
        await download_with_retry(client, video)


async def delete_service_messages():
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

    try:
        await client.start(configuration.phone)
        print(messages_el['connection_success'])

        for chat in configuration.group_chats:
            print(messages_el['retrieving_messages'].format(chat))
            async for message in client.iter_messages(chat, limit=1000):
                message.chat_name = chat
                if message.reply_to_msg_id:
                    replies_msg.append(message)
                all_messages.append(message)

        if len(all_messages) == 0:
            print('No Messages found')
            await client.send_message('me', messages_el['no_message_found'])
            return

        # Delete previously created service messages
        #await delete_service_messages()

        # Prepare video files
        await save_video_data()

        sorted_data = sorted(load_all_pickle_data(), key=lambda item: (not item[1].pinned, item[1].video_id))
        for pickle_file_name, video in sorted_data or []:

            reference_message = await client.get_messages(video.chat_name, ids=video.message_id_reference)
            video.chat_id = reference_message.chat_id
            save_pickle_data({
                'pinned': reference_message.pinned
            }, pickle_file_name,['pinned'])

            try:
                await reference_message.edit(default_video_message(video))
            except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                # Ignora l'errore se il messaggio non è stato modificato
                pass

            video.reference_message = reference_message

            # Check if the file already exists
            if os.path.exists(video.file_path):
                await add_line_to_text(reference_message, messages_el['ready_to_move'].format(video.file_name), line_for_info_data)
                print(messages['ready_to_move'].format(video.file_name))

                # Check if the file is corrupted before moving it
                if not is_file_corrupted(video.file_path, video.video_media.document.size):
                    await download_complete_action(video)
                else:
                    await add_line_to_text(reference_message, messages_el['corrupted_file'].format(video.file_name), line_for_info_data)
                    print(messages_el['corrupted_file'].format(video.file_name))
                    os.remove(video.file_path)
                continue

            # Queue the download task with the limit on simultaneous downloads
            task = download_with_limit(video)
            tasks.append(task)

        # Execute all queued tasks concurrently
        await asyncio.gather(*tasks)

    finally:
        await client.disconnect()

async def save_video_data():
    videos = []
    messages_el = configuration.messages

    for message in all_messages:
        if message.document:
            if any(isinstance(attr, DocumentAttributeVideo) for attr in message.document.attributes):
                videos.append(message)
            else:
                # Check if the document is a video based on its extension
                file_name = None
                for attr in message.media.document.attributes:
                    if isinstance(attr, DocumentAttributeFilename):
                        file_name = sanitize_filename(attr.file_name)
                        break
                if file_name and is_video_file(file_name):
                    videos.append(message)

    videos.reverse()
    videos.sort(key=lambda msg: not msg.pinned)

    print('Save video info in files')
    for video in videos:
        video_name = None
        file_name = None
        video_attribute = None

        # Important data from video
        video_id = video.id
        video_text = video.text
        video_message_document_attributes = video.media.document.attributes
        video_peer_id = video.peer_id
        video_media = video.media
        # =========================

        # Check for reply message and set like video_name
        if not video_name and len(replies_msg) > 0:
            for replyMsg in replies_msg:
                if replyMsg.reply_to_msg_id == video_id:
                    message_title = sanitize_filename(replyMsg.text.split('\n')[0].strip())
                    if message_title and not any(
                            icon in message_title for icon in ["⬇️", "‼️", "🔔", "❌", "✅", "🗜️"]):
                        video_name = message_title

        # Cerca il nome del file dal messaggio corrente
        if video_name is None:
            full_msg_rows = video_text.split('\n')
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

            video_name = sanitize_filename(msg1 + msg2 + msg3) if video_text else None

        # Codice esistente per trovare il file_name
        for attr in video_message_document_attributes:
            if isinstance(attr, DocumentAttributeFilename):
                file_name = sanitize_filename(attr.file_name)
            if isinstance(attr, DocumentAttributeVideo):
                video_attribute = attr


        # If video_name is None and file_name is not none then set file_name to video_name
        if video_name is None and file_name is not None:
            # Set video_name based on file_name if no valid video name was found
            video_name = sanitize_filename(file_name.rsplit('.', 1)[0].strip())

        # If video_name is empty send an alert message to personal chat
        if video_name is None:
            await client.send_message(
                video_peer_id,
                messages_el['empty_reference_specify_name'],
                reply_to=video_id
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

        message = await client.send_message('me', default_video_message(VideoData(**{
            "video_attribute": video_attribute,
            "pinned": video.pinned,
            "video_media": video_media,
            "video_text": video_text,
            "file_name": file_name
        })))

        video_name_cleaned = re.sub(r'[^a-zA-Z0-9\s-]', '', video_name.replace('_', ' '))

        # Creazione del dizionario contenente tutte le variabili
        video_data = {
            "message_id_reference": message.id,
            "video_id": video_id,
            "video_text": video_text,
            "video_message_document_attributes": video_message_document_attributes,
            "video_peer_id": video_peer_id,
            "video_media": video_media,
            "video_name": f'{video_text}',
            "video_name_cleaned": video_name_cleaned,
            "video_attribute": video_attribute,
            "chat_name": video.chat_name,
            "chat_id": video.chat_id,
            "file_name": file_name,
            "file_path": file_path,
            "pinned": video.pinned,
        }

        # Salvataggio del dizionario in un unico file, con il nome basato su video_id
        pickle_file_name = f"{client.api_id}_{video.chat_id}_{video_id}.pkl"
        save_pickle_data(video_data, pickle_file_name,
                         ['video_id', 'video_text', 'video_name', 'file_name', 'file_path', 'video_attribute', 'pinned', 'message_id_reference', 'video_name_cleaned'])
        if video_id:
            await client.delete_messages(video.chat_name, [video_id])



class VideoData:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<VideoData {vars(self)}>"

def load_all_pickle_data():
    # Percorso della cartella pickles
    pickles_dir = os.path.join(root_dir, 'pickles')

    # Verifica se la cartella esiste
    if not os.path.exists(pickles_dir):
        print(f"La cartella {pickles_dir} non esiste.")
        return []

    # Array per memorizzare il contenuto di ogni file pickle
    all_data = []

    # Scorre i file nella cartella pickles
    for file_name in os.listdir(pickles_dir):
        file_path = os.path.join(pickles_dir, file_name)

        # Verifica che sia un file
        if os.path.isfile(file_path):
            # Carica il contenuto del file pickle
            with open(file_path, "rb") as f:
                try:
                    data = pickle.load(f)
                    video_data = VideoData(**data)
                    all_data.append((file_name, video_data))
                except Exception as e:
                    print(f"Errore nel caricamento di {file_name}: {e}")

    return all_data

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
