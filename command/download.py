"""
Command download
"""
from func.messages import t
from func.telegram_client import edit_service_message


async def run(subcommand: str, text_input: str, extra_args=None, is_personal_chat=False, callback=None):
    """
    Run the command
    :param subcommand:
    :param text_input:
    :param extra_args:
    :param is_personal_chat:
    :param callback:
    :return:
    """
    if subcommand == 'on' or subcommand == 'start':
        await start(extra_args.get('target'))
    elif subcommand == 'off' or subcommand == 'stop':
        await stop(extra_args.get('target'))
    elif subcommand == 'rename' or subcommand == 'rn':
        await rename(extra_args.get('target'), text_input, callback)


async def start(message):
    """
    :param message:
    :return:
    """
    await edit_service_message(message, t('download_enabled'))

async def stop(message):
    """

    :param message:
    :return:
    """
    await edit_service_message(message, t('download_disabled'))


async def rename(target, text, callback):
    """
    :param target:
    :param text:
    :param callback:
    :return:
    """
    await callback(target, text)
