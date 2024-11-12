"""
Command download
"""
from typing import Union

from telethon.tl.patched import Message
from telethon.tl.types import MessageMediaDocument

from classes.object_data import ObjectData
from classes.string_builder import LINE_FOR_PINNED_VIDEO, TYPE_COMPLETED
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
    elif subcommand in ('rename', 'rn') or command == 'rename':
        await rename(extra_args.get('source_message'), text_input, callback)
    elif subcommand in ('source_message', 'dir', 'destination'):
        await target_to_download(
            extra_args.get('source_message'),
            extra_args.get('reply_message'))
    elif subcommand in ('pin', 'unpin') or command in ('pin', 'unpin'):
        await set_pinned_message(
            extra_args.get('source_message'),
            extra_args.get('reply_message'),
            subcommand == 'pin' or command == 'pin')
    elif subcommand == 'clean' or command == 'clean':
        await clear_downloads(
            extra_args.get('source_message'),
        )


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


async def target_to_download(source_message, video_object: ObjectData):
    """
    :param source_message:
    :param video_object:
    :return:
    """
    from func.main import rules_object
    completed_folder_mask = rules_object.apply_rules(
        'completed_folder_mask',
        video_object.video_name, message_id=video_object.video_id)
    await edit_service_message(source_message, completed_folder_mask or configuration.completed_folder)


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

async def clear_downloads(source_message: Union[Message, MessageMediaDocument]):
    """
    Clear completed downloads from the chat.
    :param source_message:
    :return:
    """
    messages = await fetch_all_messages(PERSONAL_CHAT_ID)

    for message in messages:
        if await get_video_status_label(message) == TYPE_COMPLETED:
            await message.delete()

    await edit_service_message(source_message, t('completed_video_cleaned'), 5)
