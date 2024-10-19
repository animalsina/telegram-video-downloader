import os
import sys

from func.messages import get_message
from func.utils import check_folder_permissions, load_config

def load_configuration():
    """
    Carica e restituisce la configurazione come un dizionario.
    """

    import run

    # Usa il nome del file di configurazione passato o il valore di default
    if len(sys.argv) > 1:
        config_file_name = sys.argv[1]
    else:
        config_file_name = 'tg-config.txt'

    # Ottieni la directory radice del progetto
    root_dir = run.root_dir

    # Percorsi relativi
    config_path = os.path.join(root_dir, config_file_name)
    file_info_path = os.path.join(root_dir, 'file_info.csv')

    # Carica la configurazione
    config = load_config(config_path)

    # Estrai le informazioni rilevanti dalla configurazione
    api_id = config.get('api_id')
    api_hash = config.get('api_hash')
    phone = config.get('phone')
    download_folder = config.get('download_folder', os.path.join(root_dir, 'tg-video'))
    completed_folder = config.get('completed_folder', os.path.join(root_dir, 'tg-video-completed'))
    check_file = os.path.join(root_dir, config.get('check_file', './downloaded_files.txt'))
    lock_file = os.path.join(root_dir, 'script.lock')
    session_name = os.path.join(root_dir, config.get('session_name', 'session_name'))
    max_simultaneous_file_to_download = int(config.get('max_simultaneous_file_to_download', 2))
    enable_video_compression = config.get('enable_video_compression', 0) == "1"
    compression_ratio = max(0, min(int(config.get('compression_ratio', 28)), 51))
    disabled = config.get('disabled', 0) == "1"
    group_chats = config.get('group_chats', [])

    # Imposta la lingua e carica i messaggi corrispondenti
    messages = get_message('')

    # Verifica le cartelle di download
    check_folder_permissions(download_folder)
    check_folder_permissions(completed_folder)

    # Restituisce tutti gli elementi come dizionario
    return Config({
        'api_id': api_id,
        'api_hash': api_hash,
        'phone': phone,
        'download_folder': download_folder,
        'completed_folder': completed_folder,
        'check_file': check_file,
        'lock_file': lock_file,
        'session_name': session_name,
        'max_simultaneous_file_to_download': max_simultaneous_file_to_download,
        'enable_video_compression': enable_video_compression,
        'compression_ratio': compression_ratio,
        'disabled': disabled,
        'group_chats': group_chats,
        'messages': messages,
        'file_info_path': file_info_path
    })
class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)