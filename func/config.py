import os
import locale

def load_config(file_path):
    config = {}
    groups = {}

    with open(file_path, 'r') as f:
        section = None
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue

            if line.startswith('[') and line.endswith(']'):
                # Section header
                section = line[1:-1].strip()
            else:
                # Key=value pair
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if section == 'groups':
                        groups[value] = key
                    else:
                        config[key] = value

    # Process min_valid_file_size_mb
    if 'min_valid_file_size_mb' in config:
        try:
            min_size_mb = float(config['min_valid_file_size_mb'])
            config['min_valid_file_size'] = min_size_mb * 1024 * 1024  # Convert MB to bytes
        except ValueError:
            config['min_valid_file_size'] = 0
    else:
        config['min_valid_file_size'] = 0

    # Add groups to config
    config['group_chats'] = groups

    return config

def get_system_language():
    lang, _ = locale.getdefaultlocale()
    if lang.startswith('it'):
        return 'it'
    return 'en'
