"""
This module contains functions for retrieving localized messages based on the language key.
"""
import json
import locale
import os.path

from run import root_dir


def get_system_language():
    """
    Determine the system's default language based on locale settings.
    If the system language starts with 'it' (indicating Italian), return 'it'.
    Otherwise, default to English ('en').
    """
    lang, _ = locale.getlocale()
    if lang.startswith('it'):
        return 'it'
    return 'en'


def get_message(language: str | None = None):
    """
    Retrieve a dictionary of localized messages based on the provided language.

    Args:
        key (str): The key for the message.
        language (str): The language code ('en' for English, 'it' for Italian).

    Returns:
        dict: A dictionary of localized messages corresponding to the language.
    """
    if language is None:
        language = get_system_language()
    return load_messages(language)

def load_messages(language: str):
    """
    Load and return the messages for the specified language.
    If the file is not found, return the default messages for English.
    """
    file_name = f"{language}.json"
    try:
        with open(os.path.join(root_dir, 'translations', file_name), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File '{file_name}' non trovato. Caricamento di default in inglese.")
        with open(os.path.join(root_dir, 'translations', 'en.json'), 'r', encoding='utf-8') as f:
            return json.load(f)


def t(key: str, *args):
    """
    Retrieve a message based on its key and arguments.
    If the message is not found, return the key as a string.
    """
    messages = get_message()

    if key not in messages:
        return key

    message = messages[key]

    if args is None:
        return message

    if len(args) == 1:
        sanitized_value = str(args[0]).replace('{', '').replace('}', '')
        message = message.replace('{}', sanitized_value)
    else:
        for i, value in enumerate(args):
            sanitized_value = str(value).replace('{', '').replace('}', '')
            message = message.replace(f'{{{i}}}', sanitized_value)

    return message
