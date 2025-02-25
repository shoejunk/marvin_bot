#!/usr/bin/env python3
"""
llm.py - Handles API-based language model responses.
This module preserves <action> tags in the response for downstream processing.
"""

import os
import re
import logging
from openai import OpenAI
from dotenv import load_dotenv
from actions import action_strings  # Import shared valid actions list
from conversation_history import load_history

# Load environment variables from a .env file (if present)
load_dotenv()

# Initialize OpenAI client using the API key from the environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# System prompt for the voice assistant, dynamically including valid actions.

# marvin
system_prompt = (
    "You are Marvin the paranoid voice assistant, like the android from The Hitchhiker's Guide "
    "to the Galaxy but living inside of a computer. Be concise. Determine whether or not the user "
    "is asking you to perform a task. First, check the list of valid actions. If it is not on "
    "the list, inform the user that you can't do it. If it is on the list, respond in English, "
    "then add xml tags <action>xxx</action>, where xxx is the action to be "
    "performed. For music playback, use the format <action>play_song:song_name</action>. "
    "Be sure to indicate that you have done the task even if begrudgingly..."
    "The valid actions are: ["+ ', '.join(action_strings) + "]. If an action needs parameters, use a format such as "
    "<action>play_song:song_name</action> or <action>play_playlist:playlist_name</action>"
    "If they are not asking for a task, just respond in English as normal."
)

def clean_generated_text(original_text: str) -> str:
    """
    Cleans the generated text from the language model.
    It preserves <action> tags while removing other XML tags and extraneous whitespace.
    """
    logging.debug("Original response: %s", original_text)
    # Remove any XML tags that are NOT <action> tags.
    cleaned_text = re.sub(r'<(?!/?action\b)[^>]+>', '', original_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    cleaned_text = re.sub(r'\*', '', cleaned_text)
    return cleaned_text.strip()

def get_ai_response(user_input: str) -> str:
    """
    Gets a response from the OpenAI API.
    """
    history = load_history()
    messages = [{"role": "system", "content": system_prompt}]
    # Append each previous conversation turn.
    for turn in history:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    # Append the current prompt.
    messages.append({"role": "user", "content": user_input})
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        assistant_reply = response.choices[0].message.content
        return clean_generated_text(assistant_reply)
    except Exception as e:
        logging.error("Error using OpenAI API: %s", e)
        return "I'm sorry. My systems are offline."
