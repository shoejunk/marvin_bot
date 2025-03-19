#!/usr/bin/env python3
"""
test_ha_integration.py - Test script for Home Assistant integration.
This script tests the Home Assistant integration with the LLM, checking context structure
and storing results.
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from home_assistant_handler import HomeAssistantHandler
from home_assistant_controller import HomeAssistantController
from context_store import update_home_assistant_query_result, get_context_for_llm, clear_context
from llm import get_ai_response

# Load environment variables
load_dotenv()

async def test_store_result():
    """Test storing a result in context."""
    print("Testing storing a result in context...")
    
    # Create a sample result
    result = {
        "success": True,
        "entity_id": "weather.home",
        "state": "sunny",
        "temperature": 75,
        "humidity": 50,
        "pressure": 1015,
        "wind_speed": 5,
        "wind_bearing": 180,
        "message": "Current weather is sunny, 75°F, 50% humidity",
    }
    
    # Store the result in context
    update_home_assistant_query_result("get_weather", result)
    
    # Get the context for LLM
    context = get_context_for_llm()
    
    # Print the context
    print("\nContext for LLM:")
    print(context)
    
    return context

async def test_list_climate_devices():
    """Test the list_climate_devices action."""
    print("\nTesting list_climate_devices...")
    
    # Create a sample result
    result = {
        "success": True,
        "count": 2,
        "devices": [
            {
                "entity_id": "climate.upper_thermostat_thermostat",
                "friendly_name": "Upper Thermostat",
                "current_temperature": 72,
                "target_temperature": 70,
                "hvac_mode": "cool",
                "hvac_action": "cooling"
            },
            {
                "entity_id": "climate.lower_thermostat_thermostat",
                "friendly_name": "Lower Thermostat",
                "current_temperature": 74,
                "target_temperature": 72,
                "hvac_mode": "cool",
                "hvac_action": "cooling"
            }
        ],
        "message": "Found 2 climate devices:\n- Upper Thermostat: Currently 72°F, set to 70°F in cool mode\n- Lower Thermostat: Currently 74°F, set to 72°F in cool mode\n"
    }
    
    # Store the result in context
    update_home_assistant_query_result("list_climate_devices", result)
    
    # Get the context for LLM
    context = get_context_for_llm()
    
    # Print the context
    print("\nContext for LLM after list_climate_devices:")
    print(context)
    
    return context

async def test_get_smart_devices():
    """Test the get_smart_devices action."""
    print("\nTesting get_smart_devices...")
    
    # Create a sample result
    result = {
        "success": True,
        "count": 10,
        "domains": {
            "light": [
                {"entity_id": "light.living_room", "friendly_name": "Living Room", "state": "on"},
                {"entity_id": "light.kitchen", "friendly_name": "Kitchen", "state": "off"}
            ],
            "switch": [
                {"entity_id": "switch.office", "friendly_name": "Office", "state": "on"},
                {"entity_id": "switch.bedroom", "friendly_name": "Bedroom", "state": "off"}
            ],
            "climate": [
                {"entity_id": "climate.upper_thermostat_thermostat", "friendly_name": "Upper Thermostat", "state": "cool"},
                {"entity_id": "climate.lower_thermostat_thermostat", "friendly_name": "Lower Thermostat", "state": "cool"}
            ]
        },
        "message": "Found 10 smart devices across 3 domains:\n\nLight (2):\n- Living Room: on\n- Kitchen: off\n\nSwitch (2):\n- Office: on\n- Bedroom: off\n\nClimate (2):\n- Upper Thermostat: cool\n- Lower Thermostat: cool\n"
    }
    
    # Store the result in context
    update_home_assistant_query_result("get_smart_devices", result)
    
    # Get the context for LLM
    context = get_context_for_llm()
    
    # Print the context
    print("\nContext for LLM after get_smart_devices:")
    print(context)
    
    return context

async def test_ha_integration():
    """Test the Home Assistant integration with the LLM."""
    print("Testing Home Assistant integration with LLM...")
    
    # Get the context
    context = await test_store_result()
    
    # Test getting a response from the LLM with the context
    try:
        response = await asyncio.wait_for(get_ai_response(
            "What's the weather like?",
            additional_context=context
        ), timeout=10)
        
        # Parse the response
        response_data = json.loads(response)
        text = response_data.get("text", "")
        
        print("\nLLM Response:")
        print(text)
    except asyncio.TimeoutError:
        print("LLM call timed out")
    except json.JSONDecodeError:
        print("Failed to parse response as JSON")
        print(response)
    
    # Test with climate devices context
    context = await test_list_climate_devices()
    try:
        response = await asyncio.wait_for(get_ai_response(
            "What thermostats do I have?",
            additional_context=context
        ), timeout=10)
        
        # Parse the response
        response_data = json.loads(response)
        text = response_data.get("text", "")
        
        print("\nLLM Response for climate devices:")
        print(text)
    except asyncio.TimeoutError:
        print("LLM call timed out")
    except json.JSONDecodeError:
        print("Failed to parse response as JSON")
        print(response)
    
    # Test with smart devices context
    context = await test_get_smart_devices()
    try:
        response = await asyncio.wait_for(get_ai_response(
            "What smart devices do I have?",
            additional_context=context
        ), timeout=10)
        
        # Parse the response
        response_data = json.loads(response)
        text = response_data.get("text", "")
        
        print("\nLLM Response for smart devices:")
        print(text)
    except asyncio.TimeoutError:
        print("LLM call timed out")
    except json.JSONDecodeError:
        print("Failed to parse response as JSON")
        print(response)

async def test_ha_handler():
    """Test the Home Assistant handler."""
    print("Testing Home Assistant handler...")
    
    # Create a controller
    ha_url = os.getenv("HOME_ASSISTANT_URL")
    ha_token = os.getenv("HOME_ASSISTANT_TOKEN")
    
    if not ha_url or not ha_token:
        print("HOME_ASSISTANT_URL or HOME_ASSISTANT_TOKEN not set in .env file")
        return
    
    controller = HomeAssistantController(ha_url, ha_token)
    
    # Create a handler
    handler = HomeAssistantHandler(controller)
    
    # Test getting weather
    print("\nTesting get_weather...")
    result = await handler.get_weather({})
    
    print("Result:")
    print(json.dumps(result, indent=2))
    
    # Get the context for LLM
    context = get_context_for_llm()
    
    print("\nContext for LLM after get_weather:")
    print(context)
    
    # Test listing climate devices
    print("\nTesting list_climate_devices...")
    result = await handler.list_climate_devices()
    
    print("Result:")
    print(json.dumps(result, indent=2))
    
    # Get the context for LLM
    context = get_context_for_llm()
    
    print("\nContext for LLM after list_climate_devices:")
    print(context)
    
    # Test getting smart devices
    print("\nTesting get_smart_devices...")
    result = await handler.get_smart_devices()
    
    print("Result:")
    print(json.dumps(result, indent=2))
    
    # Get the context for LLM
    context = get_context_for_llm()
    
    print("\nContext for LLM after get_smart_devices:")
    print(context)

async def main():
    """Main function."""
    # Clear the context first
    clear_context()
    
    # Test storing a result in context
    await test_store_result()
    
    # Test the Home Assistant integration with the LLM
    await test_ha_integration()
    
    # Test the Home Assistant handler if credentials are available
    if os.getenv("HOME_ASSISTANT_URL") and os.getenv("HOME_ASSISTANT_TOKEN"):
        await test_ha_handler()
    else:
        print("\nSkipping Home Assistant handler test (no credentials)")

if __name__ == "__main__":
    asyncio.run(main())
