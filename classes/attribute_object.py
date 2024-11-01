class AttributeObject:
    def __init__(self, **kwargs):
        self.w: int
        self.h: int
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<AttributeObject {vars(self)}>"