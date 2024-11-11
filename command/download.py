"""
Command download
"""
from func.messages import t
from func.telegram_client import edit_service_message


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
