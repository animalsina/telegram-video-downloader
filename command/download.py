"""
Command download
"""
from typing import Union

from telethon.tl.patched import Message
from telethon.tl.types import MessageMediaDocument

from classes.object_data import ObjectData
from classes.string_builder import LINE_FOR_PINNED_VIDEO, TYPE_COMPLETED, TYPE_ACQUIRED, \
    TYPE_DOWNLOADING, TYPE_DELETED, ACQUIRED_TYPES
from func.main import configuration
from func.messages import t
from func.telegram_client import edit_service_message, fetch_all_messages
from func.utils import save_video_data, add_line_to_text, get_video_status_label
from run import PERSONAL_CHAT_ID


async def run(  # pylint: disable=unused-argument
        command: str,
        subcommand: str,
        text_input: str,
        extra_args=None,
        is_personal_chat=False,
        callback=None):
    """
    Run the command
    :param command:
    :param subcommand:
    :param text_input:
    :param extra_args:
    :param is_personal_chat:
    :param callback:
    :return:
    """
    if subcommand in ('on', 'start'):
        await start(extra_args.get('source_message'), callback)
    elif subcommand in ('off', 'stop'):
        await stop(extra_args.get('source_message'), callback)
    elif subcommand in ('rename', 'rn') or command in ('rn', 'rename'):
        await rename(extra_args.get('source_message'), text_input, callback)
    elif subcommand == 'info' or command == 'info':
        await download_info(
            extra_args.get('source_message'),
            extra_args.get('reply_message'))
    elif subcommand in ('pin', 'unpin') or command in ('pin', 'unpin'):
        await set_pinned_message(
            extra_args.get('source_message'),
            extra_args.get('reply_message'),
            subcommand == 'pin' or command == 'pin')
    elif subcommand == 'clean' or command == 'clean':
        await clean_downloads(
            extra_args.get('source_message'),
        )
    elif subcommand == 'settarget' or command == 'settarget':
        await set_target_folder(
            extra_args.get('source_message'),
            text_input,
            callback
        )
    elif subcommand == 'count' or command == 'count':
        await count(extra_args.get('source_message'))
    elif subcommand == 'help' or command == 'help':
        await help(extra_args.get('source_message'))


async def start(message, callback):
    """
    :param message:
    :param callback:
    :return:
    """
    await edit_service_message(message, t('download_enabled'))
    callback()


async def stop(message, callback):
    """
    :param callback:
    :param message:
    :return:
    """
    await edit_service_message(message, t('download_disabled'))
    callback()


async def rename(source_message, text, callback):
    """
    :param source_message:
    :param text:
    :param callback:
    :return:
    """
    await callback(source_message, text)


async def download_info(source_message, video_object: ObjectData):
    """
    :param source_message:
    :param video_object:
    :return:
    """
    video_data_object = video_object
    await edit_service_message(source_message, video_data_object.to_string(), 100)


def get_completed_task_folder_path(video_object: ObjectData):
    """
    :param video_object:
    :return:
    """
    from func.main import rules_object
    return rules_object.apply_rules(
        'completed_folder_mask',
        video_object.video_name, message_id=video_object.video_id) or configuration.completed_folder


async def set_pinned_message(source_message, video_object: ObjectData, pinned: bool):
    """
    :param source_message:
    :param video_object:
    :param pinned:
    :return:
    """

    if pinned:
        await edit_service_message(source_message, t('pinned_message', video_object.video_name))
    else:
        await edit_service_message(source_message, t('unpinned_message', video_object.video_name))
    save_video_data({"pinned": pinned}, video_object, ["pinned"])
    await add_line_to_text(
        video_object.message_id_reference,
        str(pinned),
        LINE_FOR_PINNED_VIDEO, True)


async def clean_downloads(source_message: Union[Message, MessageMediaDocument]):
    """
    Clear completed downloads from the chat.
    :param source_message:
    :return:
    """
    messages = await fetch_all_messages(PERSONAL_CHAT_ID)
    download_cleaned = 0

    for message in messages:
        if await get_video_status_label(message) == TYPE_COMPLETED:
            download_cleaned += 1
            await message.delete()

    if download_cleaned == 0:
        await edit_service_message(source_message, t('no_completed_video'), 5)
        return

    await edit_service_message(source_message, t('completed_video_cleaned', download_cleaned), 5)


async def set_target_folder(source_message: Union[Message, MessageMediaDocument], text, callback):
    """
    Set target folder
    :param source_message:
    :param text:
    :param callback:
    :return:
    """
    await callback(source_message, text)


async def count(source_message: Union[Message, MessageMediaDocument]):
    """
    Get download counts
    :param source_message:
    :param callback:
    :return:
    """
    messages = await fetch_all_messages(PERSONAL_CHAT_ID)
    download_completed = 0
    download_in_progress = 0
    download_error = 0
    download_queue = 0
    download_total = 0

    for message in messages:
        if await get_video_status_label(message) == TYPE_COMPLETED:
            download_completed += 1
        elif await get_video_status_label(message) == TYPE_DOWNLOADING:
            download_in_progress += 1
        elif await get_video_status_label(message) == TYPE_DELETED:
            download_error += 1
        elif await get_video_status_label(message) == TYPE_ACQUIRED:
            download_queue += 1

        if await get_video_status_label(message) in ACQUIRED_TYPES:
            download_total += 1


    await edit_service_message(source_message,
                               t('download_count',
                                 download_completed,
                                 download_in_progress,
                                 download_error,
                                 download_total,
                                 download_queue), 15)
