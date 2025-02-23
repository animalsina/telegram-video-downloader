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

from classes.command_handler import CommandHandler
from func.telegram_client import edit_service_message

load_dotenv()

prompt_dir = os.getenv("PROMPT_FILE_DIR", "storage/prompts")
prompt_file = os.getenv("PLUGIN_GEMINI_PRE_PROMPT_FILE", "pre_video_name_gemini.prompt")
gemini_model = os.getenv("GEMINI_MODEL", "gemini-pro")
genai_api_key = os.getenv('GEMINI_API_KEY', None)
active_gemini_plugin = os.getenv("ENABLE_GEMINI_PLUGIN", None)

def init():
    """ Initialize the plugin. """

    if genai_api_key is not None:
        genai.configure(api_key=genai_api_key)
    prompt_path = os.path.join(prompt_dir, prompt_file)

    if not os.path.exists(prompt_dir):
        os.makedirs(prompt_dir)

    if not os.path.exists(prompt_path):
        with open(prompt_path, "w", encoding="utf-8") as file:
            file.write("# Example of prompt, variables is in {{variable_name}} format\n")
            file.write("Return a correct title without special characters for this video: {{query}}")

    if active_gemini_plugin is None:
        print("- Gemini Plugin is disabled; set ENABLE_GEMINI_PLUGIN=1 in .env to enable it")
    else:
        print("- Gemini Plugin")


# pre_rules_parse_video_name is the key of the plugin,
# you can find the plugin's keys in the code with apply_filters(plugin_name) method
# you can use multiple functions with plugin name in the same py file, it will be executed automatically
async def pre_rules_parse_video_name_async(video_name):  # pylint: disable=unused-argument
    """
    Plugin to parse the video name and try to find the correct title of a movie/TV series.
    Uses the Gemini AI model to analyze the name and find the correct title.
    If the title is not found, returns the original video name.
    :param video_name:
    """
    if active_gemini_plugin is None or genai_api_key is None:
        return video_name

    new_name = await gemini_return_the_title(video_name)
    if new_name is None:
        return video_name
    return new_name


async def gemini_return_the_title(query: str) -> str | None:
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
        response = await model.generate_content_async(prompt)
        if response.text == 'false':
            return None
        return response.text
    except Exception as error:  # pylint: disable=broad-exception-caught
        print("Error in gemini_return_the_title" + str(error))
        return None


def command_handler(command_handler_object: CommandHandler): # pylint: disable=unused-argument
    """
    Execute a command
    :param command_handler_object:
    :return:

    Args:
        command_handler_object:
    """
    command_handler_object.add_command(
        ["plugin:gemini:stop", "gemini:stop"],
        "Stop the gemini service plugin",
        args={},
        callback=stop_gemini_service_plugin,
    )

    command_handler_object.add_command(
        ["plugin:gemini:start","gemini:start"],
        "Start the gemini service plugin",
        args={},
        callback=start_gemini_service_plugin,
    )

# pylint: disable=unused-argument
async def stop_gemini_service_plugin(args, input_text, is_personal_chat):
    """ Stop the gemini service plugin. """
    global active_gemini_plugin # pylint: disable=global-statement
    source_message = args.get('source_message')
    print("Stopping gemini service plugin")
    if not active_gemini_plugin:
        await edit_service_message(source_message, "Gemini service plugin is not started")
        return
    await edit_service_message(source_message, "Gemini service plugin stopped")
    active_gemini_plugin = None

# pylint: disable=unused-argument
async def start_gemini_service_plugin(args, input_text, is_personal_chat):
    """ Start the gemini service plugin. """
    global active_gemini_plugin # pylint: disable=global-statement
    source_message = args.get('source_message')
    print("Starting gemini service plugin")
    if active_gemini_plugin:
        await edit_service_message(source_message, "Gemini service plugin is already started")
        return
    await edit_service_message(source_message, "Gemini service plugin started")
    active_gemini_plugin = "1"
