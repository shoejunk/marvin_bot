#!/usr/bin/env python3
"""
test_ha_context.py - Test script for Home Assistant context storage.
This script tests storing Home Assistant action results in context.
"""

import asyncio
import json
import os
from dotenv import load_dotenv
from context_store import update_home_assistant_query_result, get_context_for_llm, clear_context

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

async def main():
    """Main function."""
    # Clear the context first
    clear_context()
    
    # Test storing results in context
    await test_store_result()
    await test_list_climate_devices()
    await test_get_smart_devices()
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
