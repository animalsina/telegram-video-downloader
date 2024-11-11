"""
Command download
"""
from classes.object_data import ObjectData
from func.main import configuration
from func.messages import t
from func.telegram_client import edit_service_message, get_video_data_by_video_id, \
    get_video_data_by_message_id_reference


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
