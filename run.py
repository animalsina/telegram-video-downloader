import json
import os
import re
import sys
import asyncio
import traceback
from pathlib import Path

import telethon
from telethon.tl.types import DocumentAttributeVideo
from telethon.tl.types import DocumentAttributeFilename

from classes.attribute_object import AttributeObject
from func.config import load_configuration
from func.messages import t
from func.rules import load_rules, apply_rules
from classes.object_data import ObjectData

# Add the 'func' and 'class' directory to the system path to import custom modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'func'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'classes'))

# Import the necessary functions from custom modules
from func.utils import sanitize_filename, acquire_lock, release_lock, is_file_corrupted, \
    check_lock, is_video_file, download_complete_action, add_line_to_text, save_video_data, line_for_info_data, \
    default_video_message, remove_video_data, line_for_show_last_error, \
    video_data_file_exists_by_ref_msg_id, video_data_file_exists_by_video_id, remove_video_data_by_video_id
from func.telegram_client import create_telegram_client, download_with_retry

root_dir = os.path.dirname(os.path.abspath(__file__))

personal_chat_id = 'me'
log_in_personal_chat = True

configuration = load_configuration()
sem = asyncio.Semaphore(configuration.max_simultaneous_file_to_download)

client = create_telegram_client(configuration.session_name, configuration.api_id, configuration.api_hash)
all_messages = []
replies_msg = []
tasks = []


async def download_with_limit(video: ObjectData):
    """Download a file with concurrency limit."""

    # Inizializza il semaforo per gestire i download simultanei
    async with sem:
        # Send a status message before starting the download
        await add_line_to_text(getattr(video, 'reference_message', None), t('download_video'), line_for_info_data)

        # Start downloading the file with retry logic
        await download_with_retry(client, video)


# async def delete_service_messages():
#     """Delete service messages from Telegram that match certain icons."""
#     for message in all_messages:
#         if message.text and any(icon in message.text for icon in ["⬇️", "‼️", "🔔"]):
#             try:
#                 if log_in_personal_chat is True:
#                     await client.delete_messages(personal_chat_id, [message.id])
#                 print(f"Deleted message with id: {message.id}")
#             except Exception as delete_error:
#                 print(f"Failed to delete message with id: {message.id} - {delete_error}")


async def main():
    """Main function to manage the Telegram client and download files."""

    try:
        await client.start(configuration.phone)
        print(t('connection_success'))

        for chat in configuration.group_chats:
            print(t('retrieving_messages', chat))
            async for message in client.iter_messages(chat, limit=1000):
                message.chat_name = chat
                if message.reply_to_msg_id:
                    replies_msg.append(message)
                all_messages.append(message)

        if len(all_messages) == 0:
            print('No Messages found')
            if log_in_personal_chat is True:
                await client.send_message(personal_chat_id, t('no_message_found'))
            return

        # Delete previously created service messages
        # await delete_service_messages()

        # Prepare video files
        await save_video_data_action()
        filtered_data = [item for item in load_all_video_data() if not item[1].completed]

        sorted_data = sorted(filtered_data, key=lambda item: (not item[1].pinned, item[1].video_id))
        for video_data_file_name, video in sorted_data or []:
            video.chat_id = personal_chat_id

            if video.message_id_reference is None:
                remove_video_data_by_video_id(video.video_id)
                continue

            reference_message = await client.get_messages(personal_chat_id, ids=video.message_id_reference)

            if reference_message is None:
                remove_video_data(video)
                continue

            video.video_media = reference_message.media

            save_video_data({
                'pinned': reference_message.pinned
            }, video, ['pinned'])

            try:
                if log_in_personal_chat is True:
                    await reference_message.edit(default_video_message(video))
            except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                # Ignora l'errore se il messaggio non è stato modificato
                pass

            video.reference_message = reference_message

            # Check if the file already exists
            if os.path.exists(video.file_path):
                await add_line_to_text(reference_message, t('ready_to_move', video.file_name),
                                       line_for_info_data)
                print(t('ready_to_move', video.file_name))

                # Check if the file is corrupted before moving it
                if not is_file_corrupted(video.file_path, video.video_media.document.size):
                    await download_complete_action(video)
                else:
                    await add_line_to_text(reference_message, t('corrupted_file', video.file_name),
                                           line_for_show_last_error)
                    print(t('corrupted_file', video.file_name))
                    os.remove(video.file_path)
                continue

            # Queue the download task with the limit on simultaneous downloads
            task = asyncio.create_task(download_with_limit(video))
            tasks.append(task)

        # Execute all queued tasks concurrently
        await asyncio.gather(*tasks)

    finally:
        await client.disconnect()


async def save_video_data_action():
    """
    Action for save videos in JSON files with all useful info
    """
    videos = []

    for message in all_messages:
        if message.document and video_data_file_exists_by_ref_msg_id(message.id) is False:
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

        # Check for a reply message and set like video_name
        if not video_name and len(replies_msg) > 0:
            for reply_msg in replies_msg:
                if reply_msg.reply_to_msg_id == video_id:
                    message_title = sanitize_filename(reply_msg.text.split('\n')[0].strip())
                    # If once of the emoji is added into the message, then it will be ignored
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

        # If video_name is None and file_name is not none, then set file_name to video_name
        if video_name is None and file_name is not None:
            # Set video_name based on file_name if no valid video name was found
            video_name = sanitize_filename(file_name.rsplit('.', 1)[0].strip())

        # If video_name is empty, send an alert message to personal chat
        if video_name is None:
            if log_in_personal_chat is True:
                await client.send_message(
                    video_peer_id,
                    t('empty_reference_specify_name'),
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

        video_name_cleaned = re.sub(r'[^a-zA-Z0-9\s-]', '', video_name.replace('_', ' '))

        # Creazione del dizionario contenente tutte le variabili
        video_data = {
            "id": video_id,
            "video_id": video_id,
            "video_text": video_text,
            "video_name": video_name,
            "video_name_cleaned": video_name_cleaned,
            "chat_name": video.chat_name,
            "chat_id": personal_chat_id,
            "file_name": file_name,
            "file_path": file_path,
            "pinned": video.pinned,
            "completed": False,
            "video_attribute": None,
        }

        if video_attribute is not None:
            video_data['video_attribute'] = {
                "w": video_attribute.w,
                "h": video_attribute.h
            }

        if video_data_file_exists_by_video_id(video_data['video_id']):
            continue

        is_forward_chat_protected = False
        message = None
        video_attribute = video_data.get('video_attribute')
        if isinstance(video_attribute, dict):
            video_data_object = AttributeObject(**video_attribute)
        else:
            video_data_object = None
        try:
            if log_in_personal_chat is True:
                message = await client.send_file(
                    personal_chat_id, video_media,
                    caption=default_video_message(ObjectData(**{
                        "video_attribute": video_data_object,
                        "pinned": video.pinned,
                        "video_media": video_media,
                        "video_name": video_name_cleaned,
                        "file_name": file_name
                    })), parse_mode='Markdown')
        except telethon.errors.ChatForwardsRestrictedError:
            if log_in_personal_chat is True:
                message = await client.send_message(personal_chat_id, default_video_message(ObjectData(**{
                    "video_attribute": video_data_object,
                    "pinned": video.pinned,
                    "video_media": video_media,
                    "video_name": f'{video_name_cleaned} (**Forward Chat Protected**)',
                    "file_name": file_name,
                })))
            is_forward_chat_protected = True

        if video.pinned and message is not None:
            await message.pin()

        video_data['is_forward_chat_protected'] = is_forward_chat_protected
        if message:
            video_data['message_id_reference'] = message.id
        else:
            video_data['message_id_reference'] = video.id

        # Salvataggio del dizionario in un unico file, con il nome basato su video_id
        save_video_data(video_data, ObjectData(**video_data),
                        ['id', 'video_id', 'video_text', 'video_name', 'file_name', 'file_path', 'chat_id',
                         'chat_name', 'video_attribute', 'pinned', 'message_id_reference', 'video_name_cleaned',
                         'is_forward_chat_protected'])
        if video_id and video.chat_name == personal_chat_id and log_in_personal_chat is True:
            await client.delete_messages(video.chat_name, [video_id])


def load_all_video_data():
    # Percorso della cartella videos
    video_data_dir = os.path.join(root_dir, 'videos_data')

    # Verifica se la cartella esiste
    if not os.path.exists(video_data_dir):
        print(f"{video_data_dir} folder not exist.")
        return []

    # Array per memorizzare il contenuto di ogni file data
    all_data = []

    # Scorre i file nella cartella videos_data
    for file_name in os.listdir(video_data_dir):
        file_path = None
        if file_name.endswith('.json'):
            file_path = os.path.join(video_data_dir, file_name)
        if file_path is None:
            continue

        # Verifica che sia un file
        if os.path.isfile(file_path):
            # Carica il contenuto del file data
            with open(file_path, "rb") as f:
                try:
                    data = json.load(f)
                    object_data = ObjectData(**data)
                    if object_data.video_attribute is not None:
                        object_data_attribute = getattr(object_data, 'video_attribute')
                        object_data.video_attribute = AttributeObject(**object_data_attribute)
                    all_data.append((file_name, object_data))
                except Exception as e:
                    print(f"Errore nel caricamento di {file_name}: {e}")

    return all_data


if __name__ == '__main__':
    load_rules(Path(root_dir))
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
