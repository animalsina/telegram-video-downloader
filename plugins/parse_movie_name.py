"""
EXAMPLE OF A PLUGIN

Plugin to parse the video name and try to find the correct title of a movie/TV series.
Uses the Gemini AI model to analyze the name and find the correct title.
If the title is not found, returns the original video name.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

rules = os.getenv("PROMPT_RULES", "")
active_plugin = os.getenv("ACTIVE_PLUGIN", None)


GENAI_API_KEY = os.getenv('GEMINI_API_KEY', None)

genai.configure(api_key=GENAI_API_KEY)

rule_list = rules.splitlines() if rules else []


def parse_file_name(video_name):  # pylint: disable=unused-argument
    """
    Plugin to parse the video name and try to find the correct title of a movie/TV series.
    Uses the Gemini AI model to analyze the name and find the correct title.
    If the title is not found, returns the original video name.
    :param video_name:
    """
    if active_plugin is None:
        return video_name

    new_name = gemini_return_the_title(video_name)
    if new_name is None:
        return video_name
    return new_name


def gemini_return_the_title(query) -> str | None:
    """
    Uses the Gemini AI model to analyze the name and find the correct title.
    If the title is not found, returns None.

    Returns:
        object:
    """
    prompt = (
        f"What is the correct title of a movie or TV series called '{query}'?"
        f" From the title I provided, extract the name, look for possible associations."
        f" Perform proper analysis on the name, it likely exists even if spelled incorrectly."
        f" Just make sure that by the end of your analysis,"
        f" the resulting name is indeed a movie or TV series."
        f" In conclusion, return only the correct name with no additional text."
        f" Your output is needed to retrieve the title,"
        f" so the rest of your thoughts are unnecessary. Thank you!"
        f" Finally, if you believe the title I provided doesn't exist at all, "
        f" return a text exactly like \"false\".")

    for rule in rule_list:
        prompt += f" {rule.strip()}"

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        if response.text == 'false':
            return None
        return response.text
    except Exception:  # pylint: disable=broad-exception-caught
        return None
