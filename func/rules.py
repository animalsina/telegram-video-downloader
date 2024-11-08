"""
Rules

Apply rules to messages and files.
"""
import re
import glob
import os
from collections.abc import Iterator
from pathlib import Path
from typing import AnyStr, List, Union

from telethon.tl.custom import Forward
from telethon.tl.patched import Message
from telethon.tl.types import MessageMediaDocument, Channel

from classes.config_object import ConfigObject

rules: dict = {'message': []}


def load_rules(root_directory: Path):
    """
    Load both rules from .rule files in the specified directory.
    """

    rule_files = os.path.join(root_directory, 'rules', '*.rule')
    for rule_file in glob.glob(rule_files):
        with open(rule_file, 'r', encoding='utf-8') as f:
            set_rules(f)

    return rules

def set_rules(lines: Iterator[str]) -> None:
    """
    Set rules.
    """
    pattern = ConfigObject({
        'message': None,
        'folder': None,
        'chat_id': None,
        'chat_title': None,
        'chat_name': None,
    })
    update_data = ConfigObject({
        'pattern': pattern,
        'translate': None,
        'completed_folder_mask': None
    })

    for line in lines:
        if line.startswith('#'):
            continue
        detect_command(line, 'on:message:pattern', lambda match: setattr(pattern, 'message', match))
        detect_command(line, 'set:chat:id', lambda match: setattr(pattern, 'chat_id', match))
        detect_command(line, 'set:chat:title', lambda match: setattr(pattern, 'chat_title', match))
        detect_command(line, 'set:chat:name', lambda match: setattr(pattern, 'chat_name', match))

        if hasattr(pattern, 'message'):
            detect_command(line, 'on:folder:pattern',
                           lambda match: setattr(pattern, 'folder', match))

        detect_command(line, 'action:message:translate',
                       lambda match: setattr(update_data, 'translate', match))

        if hasattr(pattern, 'folder'):
            detect_command(line, 'action:folder:completed',
                           lambda match: setattr(update_data, 'completed_folder_mask', match))

    rules['message'].append(update_data)

def detect_command(string: str, command: str, cb: callable(str)) -> None:
    """
    Detect commands.
    """
    if string.startswith(command):
        match = re.search(r'="(.*?)"', string)
        if match:
            cb(match.group(1))  # Save the folder pattern

def safe_format(action: str, *args: tuple[AnyStr]) -> str:
    """
    Format Safe
    """
    if not re.match(r'^[^{]*({[^{}]*}|{}|[^{]*)*[^{]*$', action):
        raise ValueError("Unsafe action string.")

    return action.format(*args)


def apply_rules(type_name: str, input_value: str, chat: Union[Message, MessageMediaDocument] = None) -> str | None:
    """
    Apply rules to input and returns edited output.
    """

    # Rules for messages
    if type_name == 'translate':
        return translate_string(input_value, chat)
    if type_name == 'completed_folder_mask':
        return completed_task(input_value)
    return input_value

def completed_task(input_value: str):
    """
    Apply rules to input and returns edited output.
    """
    for rule in rules['message']:
        completed_folder_mask = rule.get('completed_folder_mask')
        if completed_folder_mask is not None:
            pattern = rule['pattern']
            match = re.match(pattern.folder, input_value)
            completed_folder = None
            if match is not None:
                for i, valore in enumerate(match.groups()):
                    if completed_folder is None:
                        completed_folder = completed_folder_mask
                    completed_folder = completed_folder.replace(f'#{i}', valore.strip())
                if completed_folder:
                    return completed_folder
    return None

def translate_string(input_value: str, chat: Union[Message, MessageMediaDocument] = None) -> str:
    """
    Apply rules to input and returns edited output.
    """
    for rule in rules['message']:
        pattern = rule.pattern
        rule_chat_id = pattern.chat_id or None
        rule_chat_title = pattern.chat_title or None
        rule_chat_name = pattern.chat_name or None
        chat_id = None
        chat_title = None
        chat_name = None
        if chat is not None and isinstance(chat, (Message, MessageMediaDocument)):
            chat_id = chat.chat_id
            forward = chat.forward
            sender = chat.forward.sender if hasattr(forward, 'sender') else None
            if chat.is_channel is True and isinstance(forward, Forward) and forward is not None:
                if forward.chat is not None:
                    chat_title = chat.forward.chat.title
                    chat_name = chat.forward.chat.username
            if chat.is_private is True and sender is not None and sender.bot is True:
                chat_title = sender.first_name
                chat_name = sender.username
        if rule_chat_id is not None and rule_chat_id != chat_id:
            continue
        if rule_chat_name is not None and rule_chat_name != chat_name:
            continue
        if rule_chat_title is not None and rule_chat_title != chat_title:
            continue
        action = rule.translate
        match = re.match(pattern.message, input_value)
        if match:
            return safe_format(action, *match.groups())
    return input_value
