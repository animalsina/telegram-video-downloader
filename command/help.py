"""
Command help
"""

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
    from func.main import command_handler
    target = extra_args.get('target')
    await edit_service_message(target, str(command_handler.list_commands()), 30)
