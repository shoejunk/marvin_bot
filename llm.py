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
    
    Note: This function is kept for backward compatibility but is primarily
    used as a fallback for the new Responses API implementation.
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
                # Check if it's a single action object (missing the standard structure)
                action_match = re.search(r'({[\s\S]*"name"[\s\S]*"parameters"[\s\S]*})', original_text)
                if action_match:
                    action_str = action_match.group(1)
                    logger.debug(f"Found single action object: {action_str}")
                    # Try to parse it as JSON
                    try:
                        action_obj = json.loads(action_str)
                        # If it has name and parameters, it's likely an action
                        if "name" in action_obj and "parameters" in action_obj:
                            # Create a proper response structure with this action
                            response_obj = {
                                "response": f"Executing {action_obj['name']} action",
                                "actions": [action_obj]
                            }
                            logger.debug(f"Created proper response structure from single action: {response_obj}")
                            return json.dumps(response_obj)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse potential action object: {action_str}")
                
                # If no JSON found, wrap the text in a basic response structure
                logger.warning("No JSON found in response, creating basic structure")
                return json.dumps({"response": original_text.strip(), "actions": []})
        
        # Fix common JSON formatting issues before parsing
        # Replace escaped quotes that break JSON parsing
        json_str = json_str.replace('\\"', '"')
        # Handle any double escaping that might occur
        json_str = json_str.replace('\\\\', '\\')
        
        # Fix issue with extra closing braces that can break JSON parsing
        # Count opening and closing braces to ensure they match
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        if close_braces > open_braces:
            # Remove excess closing braces
            excess = close_braces - open_braces
            json_str = json_str[:-excess]
            logger.debug(f"Fixed JSON by removing {excess} extra closing braces")
        
        # Parse and validate the JSON
        response_obj = json.loads(json_str)
        
        # Check if it's a single action object without proper structure
        if "name" in response_obj and "parameters" in response_obj and "response" not in response_obj and "actions" not in response_obj:
            logger.debug(f"Found single action object in JSON: {response_obj}")
            # Create a proper response structure with this action
            action_obj = response_obj
            response_obj = {
                "response": f"Executing {action_obj['name']} action",
                "actions": [action_obj]
            }
            logger.debug(f"Converted single action to proper response structure: {response_obj}")
        else:
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
    Gets a response from the OpenAI API using the new Responses API.
    
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
        
        # Import FileOperations here to avoid circular imports
        from file_operations import FileOperations
        
        # Get the list of files in the artifacts directory
        file_ops = FileOperations()
        files_list = file_ops.list_files()
        files_info = f"Files in artifacts directory: {', '.join(files_list)}"
        
        # Prepare the conversation history as input messages
        messages = []
        
        # Add conversation history (limited to last few turns for context)
        history_limit = 5  # Limit to last 5 turns for context
        for turn in history[-history_limit:]:
            # Add user message
            messages.append({
                "role": "user",
                "content": turn["user"]
            })
            
            # Extract the response text from the assistant's JSON response
            assistant_content = turn["assistant"]
            try:
                # If the assistant content is JSON, parse it to get the response
                assistant_data = json.loads(assistant_content)
                assistant_text = assistant_data.get("response", assistant_content)
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, use the content as is
                assistant_text = assistant_content
                
            # Add assistant message
            messages.append({
                "role": "assistant",
                "content": assistant_text
            })
        
        # Add system message with files info
        messages.append({
            "role": "system",
            "content": files_info
        })
        
        # Add the current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        logger.debug("Sending request to OpenAI with %d messages", len(messages))
        
        # Define the JSON schema for structured output
        json_schema = {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "The text response to be spoken to the user"
                },
                "actions": {
                    "type": "array",
                    "description": "List of actions to perform",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name of the action to perform",
                                "enum": action_strings  # Use the imported action_strings list
                            },
                            "parameters": {
                                "type": "array",
                                "description": "Parameters for the action",
                                "items": {
                                    "type": "string"
                                }
                            }
                        },
                        "required": ["name", "parameters"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["response", "actions"],
            "additionalProperties": False
        }
        
        # Try using the Responses API
        try:
            # Get response from OpenAI using the Responses API
            response = client.responses.create(
                model="gpt-4o",
                input=messages,
                instructions=personality.system_prompt,
                temperature=0.7,
                max_output_tokens=8192,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "marvin_response",
                        "schema": json_schema,
                        "strict": True
                    }
                }
            )
            
            # Extract the text content from the response
            try:
                # Get the output text from the response
                assistant_reply = response.output_text
                logger.debug("Received response from OpenAI Responses API: %s", assistant_reply)
                
                # Parse the JSON response to ensure it's valid
                try:
                    response_obj = json.loads(assistant_reply)
                    
                    # Ensure the response has the required fields
                    if "response" not in response_obj:
                        response_obj["response"] = "I'm not sure how to respond to that."
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
                    
                    # Convert to JSON string
                    cleaned_reply = json.dumps(response_obj)
                    logger.debug("Returning response: %s", cleaned_reply)
                    return cleaned_reply
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON from structured response: {e}")
                    # Fall back to the old method if structured output fails
                    return clean_generated_text(assistant_reply)
            except AttributeError as e:
                # If output_text is not available, try to extract the content from the response object
                logger.error(f"Error accessing output_text: {e}")
                logger.debug(f"Response object: {response}")
                
                # Try to access the content directly from the response
                try:
                    if hasattr(response, 'content') and response.content:
                        assistant_reply = response.content
                        logger.debug(f"Extracted content from response: {assistant_reply}")
                        return clean_generated_text(assistant_reply)
                    elif hasattr(response, 'choices') and response.choices:
                        assistant_reply = response.choices[0].message.content
                        logger.debug(f"Extracted content from choices: {assistant_reply}")
                        return clean_generated_text(assistant_reply)
                except Exception as inner_e:
                    logger.error(f"Error extracting content from response object: {inner_e}")
                
                # If we can't extract the content, return a default response
                logger.warning("Could not extract content from response object")
                return json.dumps({"response": "I'm sorry. I couldn't process your request properly.", "actions": []})
            except Exception as e:
                logger.error(f"Error extracting content from response: {e}")
                logger.debug(f"Response object: {response}")
                # If we couldn't extract a valid response, log a warning
                logger.warning("Could not extract valid response from OpenAI Responses API.")
                return json.dumps({"response": "I'm sorry. I couldn't process your request properly.", "actions": []})
                
        except Exception as e:
            # Log the error
            logger.error(f"Error using OpenAI Responses API: {e}")
            return json.dumps({"response": "I'm sorry. My systems are offline.", "actions": []})
        
    except Exception as e:
        logger.error("Error using OpenAI API: %s", e)
        return json.dumps({"response": "I'm sorry. My systems are offline.", "actions": []})