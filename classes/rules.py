"""
Rules

Apply rules to messages and files.
"""
import re
import glob
import os
from collections.abc import Iterator
from pathlib import Path
from typing import AnyStr, Optional

from classes.config_object import ConfigObject
from classes.object_data import ObjectData


class Rules:
    """
    Rules Class
    """
    def __init__(self):
        self.id_increment: int = 0
        self.rule_item_ids = {}
        self.rules = {'message': []}

    def load_rules(self, root_directory: Path):
        """
        Load both rules from .rule files in the specified directory.
        """
        from func.utils import safe_getattr

        self.rules = {'message': []}
        rule_files = os.path.join(root_directory, 'rules', '*.rule')
        for rule_file in glob.glob(rule_files):
            with open(rule_file, 'r', encoding='utf-8') as f:
                self.set_rules(f, rule_file)

        self.rules['message'] = sorted(
            self.rules['message'],
            key=lambda rule: (
                safe_getattr(rule.pattern, 'chat_id'),
                safe_getattr(rule.pattern, 'chat_name'),
                safe_getattr(rule.pattern, 'chat_title')
            ),
            reverse=True
        )

        return self

    def set_rules(self, lines: Iterator[str], rule_file: str):
        """
        Set rules.
        """
        pattern = ConfigObject({
            'message': None,
            'folder': None,
            'chat_id': None,
            'chat_title': None,
            'chat_name': None,
            'use_filename': False,
        })
        update_data = ConfigObject({
            'id': self.id_increment,
            'pattern': pattern,
            'translate': None,
            'completed_folder_mask': None,
            'file_name': rule_file
        })
        self.id_increment = self.id_increment + 1

        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                continue
            self.detect_command(line, 'on:message:pattern', lambda match: setattr(pattern, 'message', match))
            self.detect_command(line, 'set:chat:id', lambda match: setattr(pattern, 'chat_id', match))
            self.detect_command(line, 'set:chat:title', lambda match: setattr(pattern, 'chat_title', match))
            self.detect_command(line, 'set:chat:name', lambda match: setattr(pattern, 'chat_name', match))
            self.detect_command(line, 'use:message:filename', lambda match: setattr(pattern, 'use_filename', True))

            if hasattr(pattern, 'message'):
                self.detect_command(line, 'on:folder:pattern',
                               lambda match: setattr(pattern, 'folder', match))

            self.detect_command(line, 'action:message:translate',
                           lambda match: setattr(update_data, 'translate', match))

            if hasattr(pattern, 'folder'):
                self.detect_command(line, 'action:folder:completed',
                               lambda match: setattr(update_data, 'completed_folder_mask', match))

        self.rules['message'].append(update_data)
        return self

    @staticmethod
    def detect_command(string: str, command: str, cb: callable) -> None:
        """
        Detect commands.
        """
        if string.startswith(command):
            match = re.search(r'="(.*?)"', string)
            if match:
                cb(match.group(1))  # Save the folder pattern

    @staticmethod
    def safe_format(action: str, *args: tuple[AnyStr]) -> str:
        """
        Format Safe
        """
        if not re.match(r'^[^{]*({[^{}]*}|{}|[^{]*)*[^{]*$', action):
            raise ValueError("Unsafe action string.")

        return action.format(*args)

    def apply_rules(self, type_name: str, input_value: str,
                    *,
                    message_id: Optional[int] = None,
                    video_object: Optional[ObjectData] = None) -> str | None:
        """
        Apply rules to input and returns edited output.
        """

        # Rules for messages
        if type_name == 'translate':
            return self.translate_string(input_value, video_object)
        if type_name == 'completed_folder_mask':
            return self.completed_task(input_value, message_id)
        return input_value

    def completed_task(self, input_value: str, message_id: int) -> None | str:
        """
        Apply rules to input and returns edited output.
        """
        for rule in self.rules['message']:
            if message_id is None or self.rule_item_ids.get(rule.id) != message_id:
                continue
            completed_folder_mask = getattr(rule, 'completed_folder_mask')
            if completed_folder_mask is not None:
                pattern = getattr(rule, 'pattern')
                pattern_folder = getattr(pattern, 'folder') or ''
                match = re.match(pattern_folder, input_value)
                completed_folder = None
                if match is not None:
                    for i, valore in enumerate(match.groups()):
                        if completed_folder is None:
                            completed_folder = completed_folder_mask
                        completed_folder = completed_folder.replace(f'#{i}', valore.strip())
                    if completed_folder:
                        return completed_folder
        return None

    def translate_string(self, input_value: str, video_object: ObjectData) -> str:
        """
        Apply rules to input and returns edited output.
        """
        match_text = self.get_match_by_message_text(input_value, video_object)
        return match_text if match_text is not None else input_value

    def get_match_by_message_text(self, input_value: str, video_object: ObjectData) -> str:
        for rule in self.rules['message']:
            if video_object is None:
                continue
            if rule.pattern.use_filename and video_object.file_name is not None:
                input_value = video_object.file_name
            pattern = rule.pattern
            rule_chat_id = pattern.chat_id or None
            rule_chat_title = pattern.chat_title or None
            rule_chat_name = pattern.chat_name or None
            chat_id = video_object.chat_id
            chat_title = video_object.chat_title
            chat_name = video_object.chat_name
            if rule_chat_id is not None and rule_chat_id != chat_id:
                continue
            if rule_chat_name is not None and rule_chat_name != chat_name:
                continue
            if rule_chat_title is not None and rule_chat_title != chat_title:
                continue
            action = rule.translate
            match = re.match(pattern.message, input_value)
            if match:
                self.rule_item_ids[rule.id] = video_object.video_id
                return self.safe_format(action, *match.groups())

    def assign_rule_by_video_data(self, original_video_name, video_object: ObjectData):
        self.get_match_by_message_text(original_video_name, video_object)

    def reload_rules(self):
        """
        Reload rules
        :return:
        """
        from run import root_dir
        self.load_rules(root_dir)
        return self

    def get_rule_by_id(self, rule_id: int):
        """
        Get rule by id
        :param rule_id:
        :return:
        """
        for rule in self.rules['message']:
            if rule.id == rule_id:
                return rule

    def get_rule_by_item_id(self, message_id: int):
        """
        Get rule by item id
        :param message_id:
        :return:
        """
        for rule in self.rules['message']:
            if self.rule_item_ids[rule.id] == message_id:
                return rule

    def get_rules(self):
        return self.rules