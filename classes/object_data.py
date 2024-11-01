class ObjectData:
    def __init__(self, **kwargs):
        self.completed = False
        self.message_id_reference = None
        self.reference_message = None
        self.video_media = None
        self.file_name = None
        self.file_path = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<ObjectData {vars(self)}>"