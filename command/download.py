"""
Command download
"""

from classes.object_data import ObjectData
from classes.string_builder import LINE_FOR_PINNED_VIDEO
from func.main import configuration
from func.messages import t
from func.telegram_client import edit_service_message
from func.utils import save_video_data, add_line_to_text


async def run(  # pylint: disable=unused-argument
        subcommand: str,
        text_input: str,
        extra_args=None,
        is_personal_chat=False,
        callback=None):
    """
    Run the command
    :param subcommand:
    :param text_input:
    :param extra_args:
    :param is_personal_chat:
    :param callback:
    :return:
    """
    if subcommand in ('on', 'start'):
        await start(extra_args.get('target'), callback)
    elif subcommand in ('off', 'stop'):
        await stop(extra_args.get('target'), callback)
    elif subcommand in ('rename', 'rn'):
        await rename(extra_args.get('target'), text_input, callback)
    elif subcommand in ('target', 'dir', 'destination'):
        await target_to_download(extra_args.get('target'), extra_args.get('reply_message'))
    elif subcommand == 'pin' or subcommand == 'unpin':
        await set_pinned_message(extra_args.get('target'), extra_args.get('reply_message'), subcommand == 'pin')


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


async def rename(target, text, callback):
    """
    :param target:
    :param text:
    :param callback:
    :return:
    """
    await callback(target, text)


async def target_to_download(target, video_object: ObjectData):
    """
    :param target:
    :param video_object:
    :return:
    """
    from func.main import rules_object
    completed_folder_mask = rules_object.apply_rules(
        'completed_folder_mask',
        video_object.video_name, message_id=video_object.video_id)
    await edit_service_message(target, completed_folder_mask or configuration.completed_folder)


async def set_pinned_message(target, video_object: ObjectData, pinned: bool):
    """
    :param target:
    :param video_object:
    :param pinned:
    :return:
    """

    if pinned:
        await edit_service_message(target, t('pinned_message', video_object.video_name))
    else:
        await edit_service_message(target, t('unpinned_message', video_object.video_name))
    save_video_data({"pinned": pinned}, video_object, ["pinned"])
    await add_line_to_text(
        video_object.message_id_reference,
        str(pinned),
        LINE_FOR_PINNED_VIDEO, True)
