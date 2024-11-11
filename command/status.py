"""
Command status
"""
from func.main import configuration
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
    exclude_keys = ["api_id", "api_hash"]
    config_dict = vars(configuration)
    target = extra_args.get('target')

    config_text = "\n".join(
        f"{key}: {value}"
        for key, value in config_dict.items()
        if key not in exclude_keys
    )
    await edit_service_message(target, config_text, 100)
