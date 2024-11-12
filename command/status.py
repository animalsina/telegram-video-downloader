"""
Command status
"""
from func.main import configuration
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
    exclude_keys = ["api_id", "api_hash"]
    config_dict = vars(configuration)
    source_message = extra_args.get('source_message')

    config_text = "\n".join(
        f"{key}: {value}"
        for key, value in config_dict.items()
        if key not in exclude_keys
    )
    await edit_service_message(source_message, config_text, 100)
