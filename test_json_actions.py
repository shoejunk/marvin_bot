#!/usr/bin/env python3
"""
test_json_actions.py - Test the new JSON action format for Marvin.
This script simulates an LLM response with JSON actions and verifies that the parsing works correctly.
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

def test_json_response():
    """Test creating and parsing a JSON response with actions."""
    
    # Create a sample JSON response with actions
    response = {
        "response": "I've turned on the light for you, even though it's pointless since we're all going to die eventually.",
        "actions": [
            {
                "name": "turn_on_light",
                "parameters": []
            }
        ]
    }
    
    # Convert to JSON string
    json_str = json.dumps(response)
    logger.info(f"Generated JSON response: {json_str}")
    
    # Parse the JSON string back to a Python object
    parsed = json.loads(json_str)
    logger.info(f"Parsed response text: {parsed.get('response', '')}")
    
    # Extract actions
    actions = parsed.get("actions", [])
    logger.info(f"Found {len(actions)} actions")
    
    # Process each action
    for action in actions:
        action_name = action.get("name", "").lower()
        params = action.get("parameters", [])
        
        logger.info(f"Action: {action_name}, Parameters: {params}")

def test_complex_json_response():
    """Test a more complex JSON response with multiple actions and parameters."""
    
    # Create a sample complex JSON response
    response = {
        "response": "I've written your shopping list to a file and set a timer for 30 minutes.",
        "actions": [
            {
                "name": "write_file",
                "parameters": ["shopping_list.txt", "Milk\nEggs\nBread\nCoffee", "true"]
            },
            {
                "name": "set_timer",
                "parameters": ["30 minutes"]
            }
        ]
    }
    
    # Convert to JSON string
    json_str = json.dumps(response)
    logger.info(f"Generated complex JSON response: {json_str}")
    
    # Parse the JSON string back to a Python object
    parsed = json.loads(json_str)
    logger.info(f"Parsed response text: {parsed.get('response', '')}")
    
    # Extract actions
    actions = parsed.get("actions", [])
    logger.info(f"Found {len(actions)} actions")
    
    # Process each action
    for action in actions:
        action_name = action.get("name", "").lower()
        params = action.get("parameters", [])
        
        logger.info(f"Action: {action_name}, Parameters: {params}")

def test_json_extraction():
    """Test extracting JSON from different formats that the LLM might produce."""
    
    # Test case 1: JSON with code block markers
    test_case_1 = """
    I'll help you with that.
    
    ```json
    {
      "response": "I've set a timer for 5 minutes.",
      "actions": [
        {
          "name": "set_timer",
          "parameters": ["5 minutes"]
        }
      ]
    }
    ```
    """
    
    # Test case 2: JSON without code block markers
    test_case_2 = """
    {
      "response": "I've turned off the light.",
      "actions": [
        {
          "name": "turn_off_light",
          "parameters": []
        }
      ]
    }
    """
    
    # Test case 3: Text with embedded JSON
    test_case_3 = """
    Let me process your request.
    
    {
      "response": "I've searched for files containing 'python'.",
      "actions": [
        {
          "name": "search_files",
          "parameters": ["python", ""]
        }
      ]
    }
    
    Is there anything else you need?
    """
    
    # Import the function from llm.py
    from llm import clean_generated_text
    
    # Test each case
    for i, test_case in enumerate([test_case_1, test_case_2, test_case_3], 1):
        logger.info(f"Testing case {i}:")
        logger.info(f"Input: {test_case}")
        result = clean_generated_text(test_case)
        logger.info(f"Result: {result}")
        
        # Try to parse the result as JSON
        try:
            parsed = json.loads(result)
            logger.info(f"Successfully parsed as JSON: {parsed}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse as JSON: {e}")

if __name__ == "__main__":
    logger.info("Starting JSON action tests")
    test_json_response()
    logger.info("-" * 50)
    test_complex_json_response()
    logger.info("-" * 50)
    test_json_extraction()
    logger.info("Tests completed")
