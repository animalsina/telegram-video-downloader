"""
Class for storing configuration data.
"""
class ConfigObject:
    """
    Class for storing configuration data.
    """
    def __init__(self, config_dict):
        self.message = None
        for key, value in config_dict.items():
            setattr(self, key, value)
