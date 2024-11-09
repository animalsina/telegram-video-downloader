"""
Main module for run the program
"""

# Moduli standard
import asyncio
import json
import os
import shutil
import traceback
from asyncio import CancelledError, create_task
from inspect import iscoroutine
from pathlib import Path
from typing import List, Union

# Moduli di terze parti
import telethon
from telethon import events
from telethon.events import NewMessage
from telethon.tl.types import Message
from telethon.tl.types import MessageReplyHeader

# Moduli locali
from classes.object_data import ObjectData
from func.config import load_configuration
from func.messages import t
from func.rules import load_rules, reload_rules
from func.save_video_data_action import acquire_video
from func.telegram_client import (
    create_telegram_client, download_with_retry,
    send_service_message, edit_service_message, get_user_id)
from classes.string_builder import (
    LINE_FOR_VIDEO_NAME, LINE_FOR_INFO_DATA,
    StringBuilder, LINE_FOR_SHOW_LAST_ERROR)
from classes.attribute_object import AttributeObject
from func.utils import add_line_to_text, save_video_data, sanitize_video_name, sanitize_filename, remove_video_data

configuration = load_configuration()

client = create_telegram_client(
    configuration.session_name, configuration.api_id, configuration.api_hash
)
all_messages: List[Message] = []
replies_msg = []
sem = asyncio.Semaphore(configuration.max_simultaneous_file_to_download)
interrupt = False

CHECK_INTERVAL = 3

quit_program = False
start_download = True


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
            except Exception as e:
                print(f"Error downloading {video.file_name}: {e}")
                await add_line_to_text(getattr(video, "message_id_reference", None), f"Error: {e}",
                                       LINE_FOR_SHOW_LAST_ERROR)
                pass
    except Exception as e:
        print(f"Error downloading {video.file_name}: {e}")
        pass
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
        async for message in client.iter_messages(chat, limit=1000):  # type: Union[Message, MessageReplyHeader]
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
    from func.utils import (add_line_to_text, is_file_corrupted,
                            download_complete_action,
                            save_video_data, default_video_message,
                            remove_video_data, LINE_FOR_SHOW_LAST_ERROR,
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
        else:
            await add_line_to_text(
                reference_message.id,
                t("corrupted_file", video_object.file_name),
                LINE_FOR_SHOW_LAST_ERROR,
            )
            print(t("corrupted_file", video_object.file_name))
            os.remove(video_object.file_path)
        return False

    download_data = download_with_limit(video_object)

    # Queue the download task with the limit on simultaneous downloads
    return download_data if iscoroutine(download_data) else False


async def main():
    """Main function to manage the Telegram client and download files."""
    from func.save_video_data_action import save_video_data_action
    from run import root_dir, PERSONAL_CHAT_ID
    global quit_program, start_download, interrupt
    load_rules(Path(root_dir))
    videos_data = []
    run_list = []
    rules_registered: dict = {}
    can_delete_rules=False

    try:
        await client_data()
        await send_service_message(PERSONAL_CHAT_ID, t('program_start'))

        # Prepare video files
        await save_video_data_action()

        def get_video_object_by_message_id_reference(message_id_reference: str):
            for video in videos_data:
                if message_id_reference == video[1].message_id_reference:
                    return video
            return None

        async def tg_message_handler(event):
            """
            Message Handler
            """
            message_data = event.message
            user_id = await get_user_id()
            is_personal_chat = message_data.chat.id == user_id
            text = message_data.message

            if is_personal_chat:
                await edit_rules(message_data, text)
                return

        async def edit_rules(message, new_rule_text):
            nonlocal rules_registered
            if rules_registered.get(message.id):
                rule_data = rules_registered[message.id]
                with open(rule_data.file_name, 'w', encoding='utf-8') as file:
                    file.write(new_rule_text)
                await send_service_message(PERSONAL_CHAT_ID, t('rule_updated', rule_data.file_name))
                reload_rules()
                await send_service_message(PERSONAL_CHAT_ID, t('rules_reloaded'))

        @client.on(events.MessageDeleted)
        async def tg_deleted_message_handler(event): # pylint: disable=unused-function
            """Deleted Message Handler"""

            async def remove_rules(del_message_id):
                """Remove rules"""
                nonlocal rules_registered, can_delete_rules
                if rules_registered.get(del_message_id) and can_delete_rules is True:
                    rule_data = rules_registered[del_message_id]
                    shutil.move(rule_data.file_name,
                                rule_data.file_name + '.deleted')  # Move the file to a deleted folder
                    reload_rules()
                    can_delete_rules = False
                    await client.delete_messages(PERSONAL_CHAT_ID, message_ids=list(rules_registered.keys()))
                    await send_service_message(PERSONAL_CHAT_ID, t('rules_reloaded'))
                    await send_service_message(PERSONAL_CHAT_ID, t('rule_deleted', rule_data.file_name))

            for message_id in event.deleted_ids:
                remove_video_data(get_video_object_by_message_id_reference(message_id))
                await remove_rules(message_id)

        async def tg_new_message_handler(event: NewMessage.Event):
            """NewMessage Handler"""
            global quit_program, start_download, interrupt
            nonlocal run_list
            message = event.message
            user_id = await get_user_id()
            is_personal_chat = message.chat.id == user_id
            text = message.text

            if is_personal_chat:
                if text == 'help':
                    help_text = "quit: Quit the program\n" \
                                "status: Show the current configuration\n" \
                                "download:start: Start the download\n" \
                                "download:stop: Stop the download\n" \
                                "download:off: Disable the download\n" \
                                "download:on: Enable the download\n" \
                                "rules:reload: Reload the rules\n" \
                                "rules:show: Show the rules\n" \
                                "rules:add (name of file): Register a new rule\n" \
                                "rules:edit: Edit the rules\n" \
                                "rules:delete: Delete the rules\n" \
                                "rename: <name>: Rename the video\n"
                    await edit_service_message(message, help_text, 100)
                if text == 'rules:show':
                    from func.rules import rules
                    await message.delete()
                    for rule in rules['message']:
                        rules_text = (
                            f"pattern: {vars(rule.pattern)}\n"
                            f"translate: {rule.translate}\n"
                            f"completed_folder_mask: {rule.completed_folder_mask}"
                        )
                        await send_service_message(PERSONAL_CHAT_ID, rules_text, 100)
                    return
                if text == 'rules:edit':
                    from func.rules import rules
                    await message.delete()
                    await send_service_message(PERSONAL_CHAT_ID, t('rules_edit', 300), 300)
                    for rule in rules['message']:
                        with open(rule.file_name, 'r', encoding='utf-8') as file:
                            contenuto = file.read()
                        message = await send_service_message(PERSONAL_CHAT_ID, contenuto, 300)
                        rules_registered[message.id] = rule
                    return
                if text == 'rules:delete':
                    from func.rules import rules
                    nonlocal can_delete_rules
                    await message.delete()
                    await send_service_message(PERSONAL_CHAT_ID, t('rules_delete', 30), 30)
                    for rule in rules['message']:
                        message = await send_service_message(PERSONAL_CHAT_ID, rule.file_name, 30)
                        rules_registered[message.id] = rule
                    can_delete_rules=True

                    async def disable_delete_rules():
                        nonlocal can_delete_rules
                        await asyncio.sleep(30)
                        if can_delete_rules is True:
                            can_delete_rules = False
                            await send_service_message(PERSONAL_CHAT_ID, t('rules_delete_canceled'), 30)
                    asyncio.create_task(disable_delete_rules())
                    return
                if text.startswith('rules:add'):
                    rule_name = sanitize_filename(text.replace('rules:add', '')).strip()
                    path = os.path.join(root_dir, 'rules', f"{rule_name}.rule")
                    if rule_name == '':
                        await edit_service_message(message, t('rule_name_empty'))
                        return
                    if len(rule_name) > 100:
                        await edit_service_message(message, t('rule_name_too_long', 100))
                        return
                    if len(rule_name) < 3:
                        await edit_service_message(message, t('rule_name_too_short', 3))
                        return
                    if os.path.exists(path):
                        await edit_service_message(message, t('rule_already_exist', path))
                        return
                    with open(path, 'w', encoding='utf-8') as file:
                        file.write(t('rule_start_text', rule_name))
                    await edit_service_message(message, t('rule_created', rule_name))
                    await send_service_message(PERSONAL_CHAT_ID, t('rule_start_text', rule_name), 300)
                    rules_registered[message.id] = {
                        'message': {
                            'file_name': path
                        }
                    }
                    return
                if text == 'rules:reload':
                    reload_rules()
                    await edit_service_message(message, t('rules_reloaded'))
                    return
                if text == 'status':
                    exclude_keys = ["api_id", "api_hash"]
                    config_dict = vars(configuration)

                    config_text = "\n".join(
                        f"{key}: {value}"
                        for key, value in config_dict.items()
                        if key not in exclude_keys
                    )
                    await edit_service_message(message, config_text, 100)
                if text == 'quit':
                    quit_program = True
                    await edit_service_message(message, t('program_quit'))
                    return
                if text == 'download:on' or text == 'download:start':
                    start_download = True
                    interrupt = False
                    await edit_service_message(message, t('download_enabled'))
                    return
                if text == 'download:off':
                    start_download = False
                    await edit_service_message(message, t('download_disabled'))
                    return
                if text == 'download:stop':
                    start_download = False
                    interrupt = True
                    run_list = []
                    await edit_service_message(message, t('download_stopped'))
                    return
                if text.startswith('rename:'):
                    new_name = text.replace('rename:', '')
                    video_name_cleaned = sanitize_video_name(new_name)
                    if message.reply_to is not None:
                        reply_message = await client.get_messages(PERSONAL_CHAT_ID,
                                                                  ids=message.reply_to.reply_to_msg_id)
                        _, video_object = get_video_object_by_message_id_reference(reply_message.id)
                        await add_line_to_text(reply_message.id, new_name, LINE_FOR_VIDEO_NAME, True)
                        save_video_data({'video_name': new_name, 'video_name_cleaned': video_name_cleaned},
                                        video_object,
                                        ['video_name'])
                        video_object.video_name = new_name
                        await message.delete()
                    return

            await acquire_video(message)
            return

        for chat_name in configuration.group_chats:
            client.add_event_handler(
                tg_message_handler, events.MessageEdited(chats=chat_name)
            )

            client.add_event_handler(
                tg_new_message_handler, events.NewMessage(chats=chat_name)
            )

        await client.run_until_disconnected()

        while True:

            filtered_data = [
                item for item in load_all_video_data() if not item[1].completed
            ]

            sorted_data = sorted(
                filtered_data, key=lambda item: (not item[1].pinned, item[1].video_id)
            )

            videos_data = sorted_data

            if quit_program is True:
                break
            if start_download is True:
                # Name of a file, File object content
                tasks = []
                for _, video_data in videos_data or []:  # type: [str, ObjectData]
                    task = await get_video_task(video_data)
                    if task is not False and any(video_id == video_data.video_id for video_id in run_list) is False:
                        tasks.append(create_task(task))
                        run_list.append(video_data.video_id)

                # Execute all queued tasks concurrently
                try:
                    if len(tasks) > 0:
                        await asyncio.gather(*tasks, return_exceptions=True)
                except CancelledError:
                    print(t('cancel_download'))
            await asyncio.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("Script interrupted manually.")

    except Exception as error:  # pylint: disable=broad-except
        print(f"An error occurred: {error}")
        traceback.print_exc()

    finally:
        await client.disconnect()
        print("Disconnected from Telegram.")
