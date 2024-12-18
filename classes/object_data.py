"""
Module for managing object data.
"""
from typing import Optional


class ObjectData:
    """
    Class for managing object data.
    """

    def __init__(self, **kwargs):
        self.video_completed_folder = None
        self.chat_title = None
        self.forward_message_id = None
        self.video_media = None
        self.original_video_name = None
        self.chat_name = None
        self.is_forward_chat_protected = None
        self.video_id = None
        self.video_name = None
        self.video_name_cleaned = None
        self.video_attribute: Optional[dict] = None
        self.id = None
        self.chat_id = None
        self.completed = False
        self.message_id_reference = None
        self.video_media: object
        self.file_name = None
        self.file_path = None
        self.pinned = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<ObjectData {vars(self)}>"

    def to_string(self) -> str:
        """
        Returns a string representation of the object.
        :return:
        """
        return "\n".join([f"{key}: {value}" for key, value in vars(self).items()])
