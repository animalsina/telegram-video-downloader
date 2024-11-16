"""
Config module for run the program

"""
import os
import sys
from xmlrpc.client import MAXINT

from func.utils import check_folder_permissions, load_config


def load_configuration():
    """
    Carica e restituisce la configurazione come un dizionario.
    """

    import run

    lock_download = False
    # Usa il nome del file di configurazione passato o il valore di default
    if len(sys.argv) > 1:
        config_file_name = sys.argv[1]
    else:
        config_file_name = 'tg-config.txt'

    # Ottieni la directory radice del progetto
    root_dir = run.root_dir

    # Percorsi relativi
    config_path = os.path.join(root_dir, config_file_name)

    # Carica la configurazione
    config = load_config(config_path)

    # Estrai le informazioni rilevanti dalla configurazione
    api_id = config.get('api_id')
    api_hash = config.get('api_hash')
    phone = config.get('phone')
    download_folder = config.get('download_folder', os.path.join(root_dir, 'tg-video'))
    completed_folder = config.get('completed_folder', os.path.join(root_dir, 'tg-video-completed'))

    session_name = os.path.join(root_dir, config.get('session_name', 'session_name'))
    max_simultaneous_file_to_download = int(config.get('max_simultaneous_file_to_download', 2))
    max_download_size_request_limit_kb = int(config.get('max_download_size_request_limit_kb', MAXINT))
    enable_video_compression = config.get('enable_video_compression', 0) == "1"
    compression_ratio = max(0, min(int(config.get('compression_ratio', 28)), 51))
    group_chats = config.get('group_chats', [])

    # Verifica le cartelle di download
    check_folder_permissions(download_folder)
    if check_folder_permissions(completed_folder) is False:
        lock_download = True

    # Restituisce tutti gli elementi come dizionario
    return Config({
        'api_id': api_id,
        'api_hash': api_hash,
        'phone': phone,
        'download_folder': download_folder,
        'completed_folder': completed_folder,
        'session_name': session_name,
        'max_simultaneous_file_to_download': max_simultaneous_file_to_download,
        'max_download_size_request_limit_kb': max_download_size_request_limit_kb,
        'enable_video_compression': enable_video_compression,
        'compression_ratio': compression_ratio,
        'group_chats': group_chats,
        'lock_download': lock_download
    })

class Config:
    """
    Config
    """
    def __init__(self, config_dict):
        self.max_simultaneous_file_to_download = None
        self.max_download_size_request_limit_kb = MAXINT
        self.session_name = None
        self.api_id = None
        self.api_hash = None
        self.phone = None
        self.completed_folder = None
        self.enable_video_compression = False
        self.compression_ratio = 28
        self.group_chats = []
        self.download_folder = None
        self.lock_download = False
        for key, value in config_dict.items():
            setattr(self, key, value)
