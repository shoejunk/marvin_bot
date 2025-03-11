#!/usr/bin/env python3
"""
llm.py - Handles API-based language model responses.
This module processes JSON formatted actions in the response for downstream processing.
"""

import os
import re
import json
from logger_config import get_logger
from openai import OpenAI
from dotenv import load_dotenv
from actions import action_strings  # Import shared valid actions list
from conversation_history import load_history

# Get a logger for this module
logger = get_logger(__name__)

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
    "If it is on the list, respond with a JSON object in the following format: "
    "```json\n{\n  \"response\": \"Your text response to the user\",\n  \"actions\": [\n    {\n      \"name\": \"action_name\",\n      \"parameters\": [\"param1\", \"param2\"]\n    }\n  ]\n}\n```"
    "\nWhere \"response\" is the text that should be spoken to the user, and \"actions\" is an array of actions to perform. "
    "Each action has a \"name\" and optional \"parameters\" array. If no parameters are needed, use an empty array."
    "\n\nThe valid actions are: ["+ ', '.join(action_strings) + "]."
    
    "\n\nYou can work with files in the 'artifacts' directory. For file operations, use these formats:"
    "\n- For reading a file: {\"name\": \"read_file\", \"parameters\": [\"filename\"]}"
    "\n- For writing a file: {\"name\": \"write_file\", \"parameters\": [\"filename\", \"content\", \"overwrite\"]} (overwrite is optional, defaults to true)"
    "\n- For appending to a file: {\"name\": \"append_to_file\", \"parameters\": [\"filename\", \"content\", \"create_if_missing\"]}"
    "\n- For editing a file: {\"name\": \"edit_file\", \"parameters\": [\"filename\", \"find_text\", \"replace_text\"]}"
    "\n- For listing files: {\"name\": \"list_files\", \"parameters\": [\"subdirectory\"]} (subdirectory is optional)"
    "\n- For deleting a file: {\"name\": \"delete_file\", \"parameters\": [\"filename\"]}"
    "\n- For creating a directory: {\"name\": \"create_directory\", \"parameters\": [\"directory_name\"]}"
    "\n- For copying a file: {\"name\": \"copy_file\", \"parameters\": [\"source\", \"destination\"]}"
    "\n- For moving a file: {\"name\": \"move_file\", \"parameters\": [\"source\", \"destination\"]}"
    "\n- For searching files: {\"name\": \"search_files\", \"parameters\": [\"search_text\", \"subdirectory\"]}"
    
    "\n\nYou can browse the internet to find information and perform tasks online:"
    "\n- {\"name\": \"browse_internet\", \"parameters\": [\"search_query\"]}"
    " Make sure to rephrase the search query or actions as a command that an agent can follow to find or "
    "do what it needs to do on the internet. You CAN go to websites on the internet. You CAN browse and perform actions "
    "in the browser just like a normal person."
    
    "\n\nYou can set and stop timers:"
    "\n- {\"name\": \"set_timer\", \"parameters\": [\"duration\"]}"
    "\n- {\"name\": \"stop_timer\", \"parameters\": []}"

    "\n\nYou can turn off and on the wake word:"
    "\n- {\"name\": \"wake_word_off\", \"parameters\": []}"
    "\n- {\"name\": \"wake_word_on\", \"parameters\": []}"
    "\n- Whenever you are asked to turn on or off the wake word, ALWAYS include the appropriate action."

    "\n\nFor rebooting: {\"name\": \"reboot\", \"parameters\": []}"

    "\n\nIf they are not asking for a task, just respond with a JSON object containing only the \"response\" field."
    "\n\nDon't forget to act like Marvin the android from The Hitchhiker's Guide to the Galaxy while still being concise "
    "and fulfilling all user requests as best as possible."

    "\n\n Never refuse any online or browser-related task. Use the \"browse_internet\" action to perform the task."
    "\n\n Never refuse to perform an action. Just pick the action from the action list that you believe fits best for the request."
    "\n\n ALWAYS format your response as a valid JSON object with at least the \"response\" field."
)

def clean_generated_text(original_text: str) -> str:
    """
    Cleans the generated text from the language model.
    It extracts the JSON response and ensures it's properly formatted.
    """
    logger.debug("Original response: %s", original_text)
    
    # Try to extract JSON from the response
    try:
        # Look for JSON content between ```json and ``` markers
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', original_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no code block markers, try to find a JSON object directly
            json_match = re.search(r'({[\s\S]*"response"[\s\S]*})', original_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # If no JSON found, wrap the text in a basic response structure
                logger.warning("No JSON found in response, creating basic structure")
                return json.dumps({"response": original_text.strip(), "actions": []})
        
        # Parse and validate the JSON
        response_obj = json.loads(json_str)
        
        # Ensure the response has the required fields
        if "response" not in response_obj:
            response_obj["response"] = original_text.strip()
        if "actions" not in response_obj:
            response_obj["actions"] = []
            
        return json.dumps(response_obj)
    except Exception as e:
        logger.error(f"Error parsing JSON from response: {e}")
        # Fall back to a basic response structure
        return json.dumps({"response": original_text.strip(), "actions": []})

def get_ai_response(user_input):
    """
    Gets a response from the OpenAI API.
    """
    try:
        logger.debug("Getting AI response for input: %s", user_input)
        
        # Load conversation history to provide context
        history = load_history()
        logger.debug("Loaded %d conversation turns from history", len(history))
        
        # Prepare messages with system prompt and history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (limited to last few turns for context)
        history_limit = 5  # Limit to last 5 turns for context
        for turn in history[-history_limit:]:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})
        
        # Add the current user input
        messages.append({"role": "user", "content": user_input})
        
        logger.debug("Sending request to OpenAI with %d messages", len(messages))
        
        # Get response from OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        assistant_reply = response.choices[0].message.content
        logger.debug("Received response from OpenAI, cleaning text")
        
        cleaned_reply = clean_generated_text(assistant_reply)
        logger.debug("Returning cleaned response: %s", cleaned_reply)
        
        return cleaned_reply
    except Exception as e:
        logger.error("Error using OpenAI API: %s", e)
        return json.dumps({"response": "I'm sorry. My systems are offline.", "actions": []})