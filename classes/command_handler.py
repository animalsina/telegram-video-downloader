"""
CommandHandler
"""
import importlib
from typing import Any, Optional, Union, List

from telethon.tl.patched import Message
from telethon.tl.types import MessageMediaDocument

from func.telegram_client import edit_service_message

COMMAND_SPLITTER = ":"


class CommandHandler:
    """
    CommandHandler
    """

    def __init__(self):
        self.commands = {}

    async def exec(self, text_input: str, extra_args=None, is_personal_chat=False):
        """
        Execute a command
        :param callback:
        :param is_personal_chat:
        :param text_input:
        :param extra_args:
        :return:
        """
        text_input_split = text_input.split(" ", 1)
        text_lower_case = text_input_split[0].lower()
        try:
            command_data = text_lower_case.split(COMMAND_SPLITTER)

            if not self.command_exists(":".join(command_data).strip()):
                return

            module_name = self.get_module_name(":".join(command_data).strip())

            module_command = importlib.import_module(f"command.{module_name}")
            if not module_command:
                return

            await module_command.run(
                command_data[1] if len(command_data) > 1 else "",
                text_input_split[1].strip() if len(text_input_split) > 1 else "",
                extra_args,
                is_personal_chat,
                self.command_callback(":".join(command_data).strip()))
        except Exception as e: # pylint: disable=broad-except
            target = extra_args.get('target')
            if isinstance(target, Union[Message, MessageMediaDocument]):
                await edit_service_message(extra_args.get('target'), str(e))
            print(e)

    def add_command(self, command: str | List[str], description: str = '',
                    args: Optional[Any] = None, callback=None):
        """
        Add command
        command can be a string or a list, if it's a list, the first element will be the module name
            take care that the module name must be the first element of the list and it must be unique
            or it will be wrong and the command will not work as expected
        :param command:
        :param description:
        :param args:
        :param callback:
        :return:
        """
        if isinstance(command, str):
            command = [command]

        for c in command:
            self.commands[c] = {'module_name': command[0].split(COMMAND_SPLITTER)[0],
                                'description': description,
                                'args': args, 'callback': callback}

    def list_commands(self):
        """
        List commands
        :return:
        """
        command_list = "\n".join(
            f"{key}: {value['description']}" for key, value in self.commands.items()
        )
        return command_list

    def command_callback(self, command: str):
        """
        Callback
        :param command:
        :return:
        """
        return self.commands[command]['callback']

    def command_exists(self, param):
        """
        Check if command exists
        :param param:
        :return:
        """
        for command in list(self.commands.keys()):
            if command == param:
                return True
        return False

    def get_module_name(self, param):
        """
        Get module name
        :param param:
        :return:
        """
        return self.commands[param]['module_name']
