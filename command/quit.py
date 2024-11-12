"""
Command quit
"""
import asyncio

from func.messages import t
from func.telegram_client import edit_service_message


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
    source_message = extra_args.get('source_message')

    await edit_service_message(source_message, t('program_quit'), 3)
    await asyncio.sleep(4)
    callback()
