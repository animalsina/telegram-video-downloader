"""
Class for storing configuration data.
"""
from xmlrpc.client import MAXINT


class ConfigObject:
    """
    Class for storing configuration data.
    """
    def __init__(self, config_dict):
        self.message = None
        self.max_download_size_request_limit_kb = MAXINT
        for key, value in config_dict.items():
            setattr(self, key, value)
