import re
import glob
import os

rules = {'message': []}


def load_rules(root_directory):
    """
    Load both rules from .rule files in the specified directory.
    """

    rule_files = os.path.join(root_directory, 'rules', '*.rule')
    for rule_file in glob.glob(rule_files):
        with open(rule_file, 'r') as f:
            pattern = Config({
                'message': None,
                'folder': None
            })
            translate = None
            completed_folder_mask = None
            for line in f:
                if line.startswith('#'):
                    continue
                if line.startswith("on:message:pattern"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        pattern.message = match.group(1)
                if pattern.message and line.startswith("action:message:translate"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        translate = match.group(1)
                if line.startswith("on:folder:pattern"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        pattern.folder = match.group(1)
                if pattern.folder and line.startswith("action:folder:completed"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        completed_folder_mask = match.group(1)
            rules['message'].append({'pattern': pattern, 'translate': translate, 'completed_folder_mask': completed_folder_mask})
    return rules


def apply_rules(type_name, input_value):
    """
    Apply rules to input and returns edited output.
    """

    # Rules for messages
    if type_name == 'translate':
        for rule in rules['message']:
            pattern = rule['pattern']
            action = rule['translate']
            match = re.match(pattern.message, input_value)
            if match:
                return action.format(*match.groups())
    elif type_name == 'completed_folder_mask':
        for rule in rules['message']:
            completed_folder_mask = rule.get('completed_folder_mask')
            if completed_folder_mask is not None:
                pattern = rule['pattern']
                match = re.match(pattern.folder, input_value)
                completed_folder = None
                for i, valore in enumerate(match.groups()):
                    if completed_folder is None:
                        completed_folder = completed_folder_mask
                    completed_folder = completed_folder.replace(f'#{i}', valore.strip())
                if completed_folder:
                    return completed_folder
        return None
    return input_value

class Config:
    def __init__(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)