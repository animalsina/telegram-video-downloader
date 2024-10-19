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
            pattern = None
            for line in f:
                if line.startswith("on:message:pattern"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        pattern = match.group(1)
                elif pattern and line.startswith("action:message:translate"):
                    match = re.search(r'="(.*?)"', line)
                    if match:
                        action = match.group(1)
                        rules['message'].append({'pattern': pattern, 'action': action})
                        pattern = None
    return rules


def apply_rules(type_name, input_value):
    """
    Apply rules to input and returns edited output.
    """

    # Rules for messages
    if type_name == 'message':
        for rule in rules['message']:
            pattern = rule['pattern']
            action = rule['action']
            match = re.match(pattern, input_value)
            if match:
                return action.format(*match.groups())
    return input_value
