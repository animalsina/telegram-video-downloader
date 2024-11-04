import re
import glob
import os

from classes.config_object import ConfigObject

rules = {'message': []}


def load_rules(root_directory):
    """
    Load both rules from .rule files in the specified directory.
    """

    rule_files = os.path.join(root_directory, 'rules', '*.rule')
    for rule_file in glob.glob(rule_files):
        with open(rule_file, 'r') as f:
            pattern = ConfigObject({
                'message': None,
                'folder': None,
                'chat_id': None,
                'chat_title': None,
                'chat_name': None,
            })
            translate = None
            completed_folder_mask = None
            for line in f:
                if line.startswith('#'):
                    continue
                if line.startswith("on:message:pattern"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        pattern.message = match.group(1) # Save the message pattern
                if line.startswith("set:chat:id"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        pattern.chat_id = match.group(1)  # Save the chat_id
                if line.startswith("set:chat:title"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        pattern.chat_title = match.group(1)  # Save the chat_title
                if line.startswith("set:chat:name"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        pattern.chat_name = match.group(1)  # Save the chat_name
                if pattern.message and line.startswith("action:message:translate"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        translate = match.group(1) # Save the message translation
                if line.startswith("on:folder:pattern"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        pattern.folder = match.group(1) # Save the folder pattern
                if pattern.folder and line.startswith("action:folder:completed"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        completed_folder_mask = match.group(1) # Save the folder translation
            rules['message'].append(
                {'pattern': pattern, 'translate': translate, 'completed_folder_mask': completed_folder_mask})
    return rules


def safe_format(action: str, *args) -> str:
    """
    Format Safe
    """
    if not re.match(r'^[^{]*({[^{}]*}|{}|[^{]*)*[^{]*$', action):
        raise ValueError("Unsafe action string.")

    return action.format(*args)


def apply_rules(type_name, input_value, chat = None):
    """
    Apply rules to input and returns edited output.
    """

    # Rules for messages
    if type_name == 'translate':
        for rule in rules['message']:
            pattern = rule['pattern']
            rule_chat_id = pattern.chat_id or None
            rule_chat_title = pattern.chat_title or None
            rule_chat_name = pattern.chat_name or None
            chat_id = None
            chat_title = None
            chat_name = None
            if chat is not None:
                chat_id = chat.chat_id
                if chat.chat is not None:
                    chat_title = chat.chat.title
                    chat_name = chat.chat.username
            if rule_chat_id is not None and rule_chat_id != chat_id:
                continue
            if rule_chat_name is not None and rule_chat_name != chat_name:
                continue
            if rule_chat_title is not None and rule_chat_title != chat_title:
                continue
            action = rule['translate']
            match = re.match(pattern.message, input_value)
            if match:
                return safe_format(action, *match.groups())
    elif type_name == 'completed_folder_mask':
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
    return input_value
