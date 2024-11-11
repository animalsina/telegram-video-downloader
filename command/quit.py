"""
Command quit
"""
import asyncio

from func.messages import t
from func.telegram_client import edit_service_message


async def run(subcommand: str, text_input: str, extra_args=None, is_personal_chat=False, callback=None):  # pylint: disable=unused-argument
    """
    Run the command
    :param subcommand:
    :param text_input:
    :param extra_args:
    :param is_personal_chat:
    :param callback:
    :return:
    """
    target = extra_args.get('target')

    await edit_service_message(target, t('program_quit'), 3)
    await asyncio.sleep(4)
    callback()
