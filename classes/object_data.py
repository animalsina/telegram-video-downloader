from typing import Optional

from classes.attribute_object import AttributeObject


class ObjectData:
    def __init__(self, **kwargs):
        self.video_id = None
        self.video_name = None
        self.video_name_cleaned = None
        self.video_attribute: Optional[dict] = None
        self.id = None
        self.chat_id = None
        self.completed = False
        self.message_id_reference = None
        self.reference_message: object
        self.video_media: object
        self.file_name = None
        self.file_path = None
        self.pinned = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<ObjectData {vars(self)}>"