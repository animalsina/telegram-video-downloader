"""
Class for storing configuration data.
"""
class OperationStatusObject:
    """
    Class for storing configuration data.
    """
    def __init__(self, config_dict):
        self.videos_data = []
        self.run_list = []
        self.start_download = True
        self.quit_program = False
        self.message = None
        for key, value in config_dict.items():
            setattr(self, key, value)
