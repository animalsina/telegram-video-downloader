"""
Class for storing rules message data.
"""

from classes.rules_message_pattern_object import RulesMessagePatternObject


class RulesMessageObject:
    """
    Class for storing configuration data.
    """

    def __init__(self, config_dict):
        self.file_name: str | None = None
        self.id: str | None = None
        self.pattern: RulesMessagePatternObject | None = None
        self.translate: str | None = None
        self.completed_folder_mask: str | None = None

        for key, value in config_dict.items():
            setattr(self, key, value)
