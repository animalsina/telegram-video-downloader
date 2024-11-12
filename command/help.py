"""
Command help
"""

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
    from func.main import command_handler
    source_message = extra_args.get('source_message')
    await edit_service_message(source_message, str(command_handler.list_commands()), 30)
