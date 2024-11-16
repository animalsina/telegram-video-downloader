"""
Class for storing rules message pattern data.
"""


class RulesMessagePatternObject:
    """
    Class for storing configuration data.
    """

    def __init__(self, config_dict):
        self.message: str | None = None
        self.folder: str | None = None
        self.chat_id: int | None = None
        self.chat_title: str | None = None
        self.chat_name: str | None = None
        self.use_filename: bool = False
        for key, value in config_dict.items():
            setattr(self, key, value)
