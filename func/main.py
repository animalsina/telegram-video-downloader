"""
Main module for run the program
"""

# Moduli standard
import asyncio
import json
import os
import sys
import traceback
from pathlib import Path

# Moduli di terze parti
import telethon
from telethon import events

# Moduli locali
from classes.object_data import ObjectData
from func.config import load_configuration
from func.messages import t
from func.rules import load_rules
from func.telegram_client import create_telegram_client, download_with_retry
from classes.string_builder import LINE_FOR_VIDEO_NAME, LINE_FOR_INFO_DATA, StringBuilder
from classes.attribute_object import AttributeObject

configuration = load_configuration()

client = create_telegram_client(
    configuration.session_name, configuration.api_id, configuration.api_hash
)
all_messages = []
replies_msg = []
tasks = []
sem = asyncio.Semaphore(configuration.max_simultaneous_file_to_download)


def load_all_video_data() -> list:
    """
       Load all videos by config

       Returns:
           list: A list of tuples, where each tuple contains the file name and the
               ObjectData associated with the file.
       """
    from run import root_dir
    # Percorso della cartella videos
    video_data_dir = os.path.join(root_dir, "videos_data")

    # Verifica se la cartella esiste
    if not os.path.exists(video_data_dir):
        print(f"{video_data_dir} folder not exist.")
        return []

    # Array per memorizzare il contenuto di ogni file data
    all_data = []

    # Scorre i file nella cartella videos_data
    for file_name in os.listdir(video_data_dir):
        file_path = None
        if file_name.endswith(".json"):
            file_path = os.path.join(video_data_dir, file_name)
        if file_path is None:
            continue

        # Verifica che sia un file
        if os.path.isfile(file_path):
            # Carica il contenuto del file data
            with open(file_path, "rb") as file:
                try:
                    data = json.load(file)
                    object_data = ObjectData(**data)

                    # Verifica se l'attributo 'video_attribute' è un dizionario e se s ,
                    # crea un oggetto AttributeObject
                    video_attribute = getattr(object_data, "video_attribute")
                    if isinstance(video_attribute, dict):
                        object_data.video_attribute = AttributeObject(**video_attribute)

                    all_data.append((file_name, object_data))
                except Exception as error2:  # pylint: disable=broad-except
                    print(f"Errore nel caricamento di {file_name}: {error2}")

    return all_data


async def download_with_limit(video: ObjectData):
    """Download a file with concurrency limit."""
    from func.utils import add_line_to_text

    # Inizializza il semaforo per gestire i download simultanei
    async with sem:
        # Send a status message before starting the download
        await add_line_to_text(
            getattr(video, "reference_message", None),
            t("download_video"),
            LINE_FOR_INFO_DATA,
        )

        # Start downloading the file with retry logic
        await download_with_retry(client, video)

async def client_data():
    """
    Client data
    """
    from run import PERSONAL_CHAT_ID, LOG_IN_PERSONAL_CHAT

    await client.start(configuration.phone)
    print(t("connection_success"))

    for chat in configuration.group_chats:
        print(t("retrieving_messages", chat))
        async for message in client.iter_messages(chat, limit=1000):
            message.chat_name = chat
            if message.reply_to_msg_id:
                replies_msg.append(message)
            all_messages.append(message)

    if len(all_messages) == 0:
        print(t("no_message_found"))
        if LOG_IN_PERSONAL_CHAT is True:
            await client.send_message(PERSONAL_CHAT_ID, t("no_message_found"))
        return

    # Delete previously created service messages
    # await delete_service_messages()

async def get_video_task(video_data):
    """
    Get the video task
    """
    from run import PERSONAL_CHAT_ID, LOG_IN_PERSONAL_CHAT
    from func.utils import (add_line_to_text, is_file_corrupted,
                            download_complete_action,
                            save_video_data, default_video_message,
                            remove_video_data, LINE_FOR_SHOW_LAST_ERROR,
                            remove_video_data_by_video_id)
    video = video_data[1]  # type: ObjectData
    video.chat_id = PERSONAL_CHAT_ID

    if video.message_id_reference is None:
        remove_video_data_by_video_id(video.video_id)
        return False

    reference_message = await client.get_messages(
        PERSONAL_CHAT_ID, ids=video.message_id_reference
    )

    if reference_message is None:
        remove_video_data(video)
        return False

    if video.is_forward_chat_protected is not True:
        video.video_media = reference_message.media
    else:
        video_data = await client.get_messages(
            video.chat_name, ids=video.video_id
        )
        video.video_media = video_data.media

    save_video_data({"pinned": reference_message.pinned}, video, ["pinned"])

    try:
        if LOG_IN_PERSONAL_CHAT is True:
            await reference_message.edit(default_video_message(video))
    except telethon.errors.rpcerrorlist.MessageNotModifiedError:
        # Ignora l'errore se il messaggio non è stato modificato
        pass

    video.reference_message = reference_message
    document = getattr(video.video_media, 'document', None)

    # Check if the file already exists
    if os.path.exists(video.file_path):
        await add_line_to_text(
            reference_message,
            t("ready_to_move", video.file_name),
            LINE_FOR_INFO_DATA,
        )
        print(t("ready_to_move", video.file_name))

        # Check if the file is corrupted before moving it
        if not is_file_corrupted(
                video.file_path, document.size
        ):
            await download_complete_action(video)
        else:
            await add_line_to_text(
                reference_message,
                t("corrupted_file", video.file_name),
                LINE_FOR_SHOW_LAST_ERROR,
            )
            print(t("corrupted_file", video.file_name))
            os.remove(video.file_path)
        return False

    # Queue the download task with the limit on simultaneous downloads
    return asyncio.create_task(download_with_limit(video))

async def main():
    """Main function to manage the Telegram client and download files."""
    from func.save_video_data_action import save_video_data_action
    from run import root_dir, PERSONAL_CHAT_ID
    from func.utils import check_lock, acquire_lock, release_lock
    load_rules(Path(root_dir))
    lock_file = configuration.lock_file
    if configuration.disabled:
        print("Disabled")
        sys.exit(0)

    check_lock(lock_file)
    acquire_lock(lock_file)

    try:
        await client_data()
        # Prepare video files
        await save_video_data_action()
        filtered_data = [
            item for item in load_all_video_data() if not item[1].completed
        ]

        sorted_data = sorted(
            filtered_data, key=lambda item: (not item[1].pinned, item[1].video_id)
        )

        videos_data = sorted_data

        async def tg_message_handler(event):
            """
            Message Handler
            """
            message_data = event.message
            text = message_data.message
            builder = StringBuilder(text)
            video_name = builder.get_line(LINE_FOR_VIDEO_NAME)
            print(video_name)

        client.add_event_handler(
            tg_message_handler, events.MessageEdited(chats=PERSONAL_CHAT_ID)
        )

        # Name of a file, File object content
        for video_data in videos_data or []:  # type: [str, ObjectData]
            tasks.append(get_video_task(video_data))

        # Execute all queued tasks concurrently
        await asyncio.gather(*tasks)
        release_lock(lock_file)
    except KeyboardInterrupt:
        print("Script interrupted manually.")
        release_lock(lock_file)

    except Exception as error:  # pylint: disable=broad-except
        print(f"An error occurred: {error}")
        traceback.print_exc()
        release_lock(lock_file)

    finally:
        await client.disconnect()
        print("Disconnected from Telegram.")
        release_lock(lock_file)
