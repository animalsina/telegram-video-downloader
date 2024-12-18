"""
Class for storing configuration data.
"""
class OperationStatusObject:
    """
    Class for storing configuration data.
    """
    def __init__(self, config_dict):
        self.can_delete_rules = False
        self.videos_data = []
        self.start_download = True
        self.quit_program = False
        self.message = None
        self.rules_registered = {}
        for key, value in config_dict.items():
            setattr(self, key, value)
