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
from personalities import get_personality

# Get a logger for this module
logger = get_logger(__name__)

# Load environment variables from a .env file (if present)
load_dotenv()

# Initialize OpenAI client using the API key from the environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get the default personality's system prompt
system_prompt = get_personality().system_prompt

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
        
        # Fix common JSON formatting issues before parsing
        # Replace escaped quotes that break JSON parsing
        json_str = json_str.replace('\\"', '"')
        # Handle any double escaping that might occur
        json_str = json_str.replace('\\\\', '\\')
        
        # Parse and validate the JSON
        response_obj = json.loads(json_str)
        
        # Ensure the response has the required fields
        if "response" not in response_obj:
            response_obj["response"] = original_text.strip()
        if "actions" not in response_obj:
            response_obj["actions"] = []
            
        # Validate each action to ensure it has the required fields
        validated_actions = []
        for action in response_obj.get("actions", []):
            if isinstance(action, dict) and "name" in action:
                # Ensure parameters is a list
                if "parameters" not in action or not isinstance(action["parameters"], list):
                    action["parameters"] = []
                validated_actions.append(action)
                logger.debug(f"Validated action: {action}")
            else:
                logger.warning(f"Skipping invalid action: {action}")
                
        response_obj["actions"] = validated_actions
        
        # Log the final response object for debugging
        logger.debug(f"Final response object: {response_obj}")
            
        return json.dumps(response_obj)
    except Exception as e:
        logger.error(f"Error parsing JSON from response: {e}")
        # Fall back to a basic response structure
        return json.dumps({"response": original_text.strip(), "actions": []})

def get_ai_response(user_input, personality_name=None):
    """
    Gets a response from the OpenAI API.
    
    Args:
        user_input (str): The user's input text
        personality_name (str, optional): Name of the personality to use. Defaults to None.
    
    Returns:
        str: The AI's response as a JSON string
    """
    try:
        logger.debug("Getting AI response for input: %s", user_input)
        
        # Get the specified personality or default
        personality = get_personality(personality_name)
        logger.debug(f"Using personality: {personality.name}")
        
        # Load conversation history to provide context
        history = load_history()
        logger.debug("Loaded %d conversation turns from history", len(history))
        
        # Prepare messages with system prompt and history
        messages = [{"role": "system", "content": personality.system_prompt}]
        
        # Add conversation history (limited to last few turns for context)
        history_limit = 5  # Limit to last 5 turns for context
        for turn in history[-history_limit:]:
            messages.append({"role": "user", "content": turn["user"]})
            
            # Extract the response text from the assistant's JSON response
            assistant_content = turn["assistant"]
            try:
                # If the assistant content is JSON, parse it to get the response
                assistant_data = json.loads(assistant_content)
                assistant_text = assistant_data.get("response", assistant_content)
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, use the content as is
                assistant_text = assistant_content
                
            messages.append({"role": "assistant", "content": assistant_text})
        
        # Import FileOperations here to avoid circular imports
        from file_operations import FileOperations
        
        # Get the list of files in the artifacts directory
        file_ops = FileOperations()
        files_list = file_ops.list_files()
        files_info = f"Files in artifacts directory: {', '.join(files_list)}"
        
        # Add the artifacts directory contents as context
        messages.append({"role": "system", "content": files_info})
        
        # Add the current user input
        messages.append({"role": "user", "content": user_input})
        
        logger.debug("Sending request to OpenAI with %d messages", len(messages))
        
        # Get response from OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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