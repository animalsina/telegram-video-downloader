"""
Main module for run the program
"""

# Moduli standard
import asyncio
import os
import shutil
import traceback
from asyncio import CancelledError, create_task
from pathlib import Path
from typing import List

# Moduli di terze parti
import telethon
from telethon import events
from telethon.events import NewMessage
from telethon.tl.types import Message

from classes.command_handler import CommandHandler
# Moduli locali
from classes.object_data import ObjectData
from classes.operation_status_object import OperationStatusObject
from func.command_declaration import command_declaration
from func.config import load_configuration
from func.messages import t
from classes.rules import Rules
from func.save_video_data_action import acquire_video
from func.telegram_client import (
    create_telegram_client, download_with_retry,
    send_service_message, get_user_id,
    get_video_data_by_message_id_reference)
from classes.string_builder import (
    LINE_FOR_INFO_DATA,
    LINE_FOR_SHOW_LAST_ERROR)
from func.utils import add_line_to_text, save_video_data, remove_video_data, get_video_object_by_message_id_reference

configuration = load_configuration()

client = create_telegram_client(
    configuration.session_name, configuration.api_id, configuration.api_hash
)

# Initialize rules
rules_object = Rules()

command_handler = CommandHandler()

all_messages: List[Message] = []
replies_msg = []
operation_status = OperationStatusObject({
    'can_delete_rules': False,
    'interrupt': False,
    'quit_program': False,
    'start_download': True,
    'run_list': [],
    'rules_registered': {},
})
sem = asyncio.Semaphore(configuration.max_simultaneous_file_to_download)

CHECK_INTERVAL = 3


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
        if file_path is not None:
            message_id_reference = int(os.path.basename(file_path).split("_")[0])
            all_data.append((file_name, get_video_data_by_message_id_reference(message_id_reference)))
    return all_data


async def download_with_limit(video: ObjectData):
    """Download a file with concurrency limit."""

    # Inizializza il semaforo per gestire i download simultanei
    try:
        async with sem:
            # Send a status message before starting the download
            try:
                await add_line_to_text(
                    getattr(video, "message_id_reference", None),
                    t("download_video"),
                    LINE_FOR_INFO_DATA,
                )

                # Start downloading the file with retry logic
                await download_with_retry(client, video)
            except Exception as e:  # pylint: disable=broad-except
                operation_status.run_list.remove(video.video_id)
                print(f"Error downloading {video.file_name}: {e}")
                await add_line_to_text(getattr(video, "message_id_reference", None), f"Error: {e}",
                                       LINE_FOR_SHOW_LAST_ERROR)
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error downloading {video.file_name}: {e}")
        await add_line_to_text(getattr(video, "message_id_reference", None), f"Error: {e}",
                               LINE_FOR_SHOW_LAST_ERROR)
        operation_status.run_list.remove(video.video_id)
    finally:
        # Eventualmente liberare altre risorse
        pass


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


async def get_video_task(video_object: ObjectData):
    """
    Get the video task
    """
    from run import PERSONAL_CHAT_ID, LOG_IN_PERSONAL_CHAT
    from func.utils import (is_file_corrupted,
                            download_complete_action,
                            default_video_message,
                            remove_video_data_by_video_id)

    if video_object.message_id_reference is None:
        remove_video_data_by_video_id(video_object.video_id)
        return False

    reference_message = await client.get_messages(
        PERSONAL_CHAT_ID, ids=video_object.message_id_reference
    )

    if reference_message is None:
        remove_video_data(video_object)
        return False

    if video_object.is_forward_chat_protected is not True:
        video_object.video_media = reference_message.media
    else:
        video_data = await client.get_messages(
            video_object.chat_name, ids=video_object.video_id
        )
        if video_data is not None:
            video_object.video_media = video_data.media
        else:  # if reference not exists when is forward chat protected, remove video json from folder
            await reference_message.delete()
            remove_video_data(video_object)
            return False

    rules_object.assign_rule_by_video_data(video_object.original_video_name, video_object)
    save_video_data({"pinned": reference_message.pinned}, video_object, ["pinned"])

    try:
        if LOG_IN_PERSONAL_CHAT is True:
            await reference_message.edit(default_video_message(video_object))
    except telethon.errors.rpcerrorlist.MessageNotModifiedError:
        # Ignora l'errore se il messaggio non è stato modificato
        pass

    document = getattr(video_object.video_media, 'document', None)

    # Check if the file already exists
    if os.path.exists(video_object.file_path):
        await add_line_to_text(
            reference_message.id,
            t("ready_to_move", video_object.file_name),
            LINE_FOR_INFO_DATA,
        )
        print(t("ready_to_move", video_object.file_name))

        # Check if the file is corrupted before moving it
        if not is_file_corrupted(
                video_object.file_path, document.size
        ):
            return await download_complete_action(video_object)

        await add_line_to_text(
            reference_message.id,
            t("corrupted_file", video_object.file_name),
            LINE_FOR_SHOW_LAST_ERROR,
        )
        print(t("corrupted_file", video_object.file_name))
        os.remove(video_object.file_path)
        return False

    # Queue the download task with the limit on simultaneous downloads
    return video_object

async def main():  # pylint: disable=unused-argument, too-many-statements
    """Main function to manage the Telegram client and download files."""
    from func.save_video_data_action import save_video_data_action
    from run import root_dir, PERSONAL_CHAT_ID

    rules_object.load_rules(Path(root_dir), True)
    operation_status.videos_data = []
    operation_status.rules_registered = {}

    await command_declaration()

    try:
        await client_data()
        await send_service_message(PERSONAL_CHAT_ID, t('program_start'), 5)

        # Prepare video files
        await save_video_data_action()

        async def tg_message_handler(event):
            """
            Message Handler
            """
            message_data = event.message
            user_id = await get_user_id()
            is_personal_chat = message_data.chat.id == user_id
            text = message_data.message

            if is_personal_chat:
                if operation_status.rules_registered.get(message_data.id):
                    rule_data = operation_status.rules_registered[message_data.id]
                    with open(rule_data.file_name, 'w', encoding='utf-8') as file:
                        file.write(text)
                    await send_service_message(PERSONAL_CHAT_ID, t('rule_updated', rule_data.file_name))
                    rules_object.reload_rules()
                    await send_service_message(PERSONAL_CHAT_ID, t('rules_reloaded'))
                return

        @client.on(events.MessageDeleted)
        async def tg_deleted_message_handler(event):  # pylint: disable=unused-argument
            """Deleted Message Handler"""

            async def remove_rules(del_message_id):
                """Remove rules"""
                if (operation_status.rules_registered.get(del_message_id) and
                        operation_status.can_delete_rules is True):
                    rule_data = operation_status.rules_registered[del_message_id]
                    shutil.move(rule_data.file_name,
                                rule_data.file_name + '.deleted')  # Move the file to a deleted folder
                    rules_object.reload_rules()
                    operation_status.can_delete_rules = False
                    await client.delete_messages(PERSONAL_CHAT_ID,
                                                 message_ids=list(operation_status.rules_registered.keys()))
                    await send_service_message(PERSONAL_CHAT_ID, t('rules_reloaded'))
                    await send_service_message(PERSONAL_CHAT_ID, t('rule_deleted', rule_data.file_name))

            for message_id in event.deleted_ids:
                remove_video_data(get_video_object_by_message_id_reference(message_id))
                await remove_rules(message_id)

        async def tg_new_message_handler(event: NewMessage.Event):
            """NewMessage Handler"""
            message = event.message
            user_id = await get_user_id()
            is_personal_chat = message.chat.id == user_id
            text = message.text

            await command_handler.exec(text, {'target': message}, is_personal_chat)
            await acquire_video(message)
            return

        for chat_name in configuration.group_chats:
            client.add_event_handler(
                tg_message_handler, events.MessageEdited(chats=chat_name)
            )

            client.add_event_handler(
                tg_new_message_handler, events.NewMessage(chats=chat_name)
            )

        while True:
            filtered_data = [
                item for item in load_all_video_data() if not item[1].completed
            ]

            sorted_data = sorted(
                filtered_data, key=lambda item: (not item[1].pinned, item[1].video_id)
            )

            operation_status.videos_data = sorted_data

            if operation_status.quit_program is True:
                break
            if operation_status.start_download is True:
                # Name of a file, File object content
                tasks = []
                for _, video_data in operation_status.videos_data or []:  # type: [str, ObjectData]
                    task_video_data = await get_video_task(video_data)
                    if task_video_data is not False and any(
                            video_id == video_data.video_id for video_id in operation_status.run_list
                    ) is False:
                        tasks.append(create_task(download_with_limit(task_video_data)))
                        operation_status.run_list.append(video_data.video_id)

                # Execute all queued tasks concurrently
                try:
                    if len(tasks) > 0:
                        await asyncio.gather(*tasks, return_exceptions=True)
                except CancelledError:
                    print(t('cancel_download'))
                    operation_status.run_list = []
            await asyncio.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        operation_status.run_list = []
        print("Script interrupted manually.")

    except Exception as error:  # pylint: disable=broad-except
        print(f"An error occurred: {error}")
        operation_status.run_list = []
        traceback.print_exc()

    finally:
        await client.disconnect()
        print("Disconnected from Telegram.")
