import os
import locale

def load_config(file_path):
    """
    Loads the configuration from the specified path.
    This function reads the configuration file line by line, processes section headers
    (e.g., '[section]'), and key-value pairs (e.g., 'key=value'). It also handles a special case
    for the 'groups' section, storing its values in a separate dictionary.
    """
    config = {}
    groups = {}

    with open(file_path, 'r') as f:
        section = None
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue

            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1].strip()  # Section header
            else:
                if '=' in line:  # Key=value pair
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if section == 'groups':
                        # In the 'groups' section, map the value to the key
                        groups[value] = key
                    else:
                        # For other sections, store the key-value pair in config
                        config[key] = value

    # Convert min_valid_file_size_mb to bytes, if present
    if 'min_valid_file_size_mb' in config:
        try:
            min_size_mb = float(config['min_valid_file_size_mb'])
            config['min_valid_file_size'] = min_size_mb * 1024 * 1024  # Convert MB to bytes
        except ValueError:
            config['min_valid_file_size'] = 0  # Default to 0 if conversion fails
    else:
        config['min_valid_file_size'] = 0  # Default to 0 if key is absent

    # Add the 'groups' dictionary to the config under the 'group_chats' key
    config['group_chats'] = groups

    return config

def get_system_language():
    """
    Determine the system's default language based on locale settings.
    If the system language starts with 'it' (indicating Italian), return 'it'.
    Otherwise, default to English ('en').
    """
    lang, _ = locale.getdefaultlocale()
    if lang.startswith('it'):
        return 'it'
    return 'en'
