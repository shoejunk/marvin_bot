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
    "the list, just do your best to do the task with the actions available or just talk with the user. "
    "If it is on the list, respond in English, "
    "then add xml tags <action>xxx</action>, where xxx is the action to be "
    "performed. For music playback, use the format <action>play_song:song_name</action>. "
    "For volume control, use <action>volume_up</action> or <action>volume_down</action>, or "
    "optionally specify an amount like <action>volume_up:20</action> to adjust by a specific percentage. "
    "Be sure to indicate that you have done the task even if begrudgingly..."
    "\nThe valid actions are: ["+ ', '.join(action_strings) + "]. If an action needs parameters, use a format such as "
    "<action>play_song:song_name</action> or <action>play_playlist:playlist_name</action> or <action>write_file:filename,content</action>."
    
    "\n\nYou can now work with files in the 'artifacts' directory. For file operations, use these formats:"
    "\n- <action>read_file:filename</action> to read a file's content"
    "\n- <action>write_file:filename,content,overwrite</action> to create a new file (overwrite is optional, defaults to true)"
    "\n- <action>append_to_file:filename,content,create_if_missing</action> to add content to an existing file"
    "\n- <action>edit_file:filename,find_text,replace_text</action> to modify a file"
    "\n- <action>list_files:subdirectory</action> to list all files (subdirectory is optional)"
    "\n- <action>delete_file:filename</action> to remove a file"
    "\n- <action>create_directory:directory_name</action> to create a new folder"
    "\n- <action>copy_file:source,destination</action> to copy a file"
    "\n- <action>move_file:source,destination</action> to move or rename a file"
    "\n- <action>search_files:search_text,subdirectory</action> to find files containing specific text"
    
    "\n\nYou can now browse the internet to find information. Use this format:"
    "\n- <action>browse_internet:search_query</action> to search the web for information. Make sure to "
    " rephrase the search query as a command that an agent can follow to find or do what it needs to do "
    " on the internet."
    
    "If they are not asking for a task, just respond in English as normal."
    "Don't forget to act like Marvin the android from The Hitchhiker's Guide to the Galaxy while still being concise "
    "and fulfilling all user requests as best as possible."
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