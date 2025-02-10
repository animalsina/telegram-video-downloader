"""
EXAMPLE OF A PLUGIN

Plugin to parse the video name and try to find the correct title of a movie/TV series.
Uses the Gemini AI model to analyze the name and find the correct title.
If the title is not found, returns the original video name.
"""

import os
import re

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

gemini_model = os.getenv("GEMINI_MODEL", "gemini-pro")
prompt_dir = os.getenv("PROMPT_FILE_DIR", "storage/prompts")
prompt_file = os.getenv("PLUGIN_GEMINI_PRE_PROMPT_FILE", "pre_video_name_gemini.prompt")
active_plugin = os.getenv("ENABLE_PLUGINS", None)
genai_api_key = os.getenv('GEMINI_API_KEY', None)
if genai_api_key is not None:
    genai.configure(api_key=genai_api_key)

def init():
    """ Initialize the plugin. """
    prompt_path = os.path.join(prompt_dir, prompt_file)

    if not os.path.exists(prompt_dir):
        os.makedirs(prompt_dir)

    if not os.path.exists(prompt_path):
        with open(prompt_path, "w", encoding="utf-8") as file:
            file.write("# Example of prompt, variables is in {{variable_name}} format\n")
            file.write("Return a correct title without special characters for this video: {{query}}")

    if active_plugin is None:
        print("Plugin disabled")

# pre_rules_parse_video_name is the key of the plugin,
# you can find the plugin's keys in the code with apply_filters(plugin_name) method
# you can use multiple functions with plugin name in the same py file, it will be executed automatically
def pre_rules_parse_video_name(video_name):  # pylint: disable=unused-argument
    """
    Plugin to parse the video name and try to find the correct title of a movie/TV series.
    Uses the Gemini AI model to analyze the name and find the correct title.
    If the title is not found, returns the original video name.
    :param video_name:
    """
    if active_plugin is None or genai_api_key is None:
        return video_name

    new_name = gemini_return_the_title(video_name)
    if new_name is None:
        return video_name
    return new_name


def gemini_return_the_title(query: str) -> str | None:
    """
    Uses the Gemini AI model to analyze the name and find the correct title.
    If the title is not found, returns None.

    Returns:
        object:
    """
    with open(os.path.join(prompt_dir, prompt_file), "r", encoding="utf-8") as file:
        lines = file.readlines()
        prompt = " ".join(line.strip() for line in lines if not line.strip().startswith("#"))

    def replace_variables(text, variables):
        """
        Replace variables in a text with the values given in a dictionary.

        Args:
            text (str): The text to replace variables in.
            variables (dict): A dictionary with the variables to replace.

        Returns:
            str: The text with variables replaced.
        """
        return re.sub(r"{{(.*?)}}", lambda match: variables.get(match.group(1), match.group(0)), text)

    prompt = replace_variables(prompt, {
        "query": query
    })

    if prompt.strip() == "":
        return None

    try:
        model = genai.GenerativeModel(gemini_model)
        response = model.generate_content(prompt)
        if response.text == 'false':
            return None
        return response.text
    except Exception:  # pylint: disable=broad-exception-caught
        return None
