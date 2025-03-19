#!/usr/bin/env python3
"""
context_store.py - Manages persistent context data for the LLM.
This module provides storage for information that should be included with every LLM call,
regardless of conversation history limits.
"""

import json
import os
import time
import datetime
from typing import Dict, Any, List
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

# File to store persistent context
CONTEXT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persistent_context.json")

# Default context structure
DEFAULT_CONTEXT = {
    "home_assistant": {
        "devices": {},
        "services": {},
        "climate_devices": [],
        "query_results": {}
    },
    "system": {}
}

# Custom JSON encoder to handle complex objects
class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects and other complex types."""
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        # Handle any other non-serializable objects
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

def _sanitize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a result dictionary to ensure it can be safely serialized to JSON.
    Removes problematic fields and truncates large values.
    
    Args:
        result (Dict[str, Any]): The result to sanitize
        
    Returns:
        Dict[str, Any]: The sanitized result
    """
    if not result or not isinstance(result, dict):
        return result
        
    sanitized = {}
    
    for key, value in result.items():
        # Skip problematic keys that might cause serialization issues
        if key in ["context"]:
            continue
            
        # Handle nested dictionaries
        if isinstance(value, dict):
            sanitized[key] = _sanitize_result(value)
        # Handle lists of dictionaries
        elif isinstance(value, list):
            if all(isinstance(item, dict) for item in value):
                sanitized[key] = [_sanitize_result(item) for item in value]
            else:
                # Handle lists of mixed types
                sanitized_list = []
                for item in value:
                    if isinstance(item, dict):
                        sanitized_list.append(_sanitize_result(item))
                    elif isinstance(item, (datetime.datetime, datetime.date, datetime.time)):
                        sanitized_list.append(item.isoformat())
                    elif not isinstance(item, (str, int, float, bool, type(None))):
                        sanitized_list.append(str(item))
                    else:
                        sanitized_list.append(item)
                sanitized[key] = sanitized_list
        # Handle other values
        else:
            # Convert any complex objects to strings
            if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
                sanitized[key] = value.isoformat()
            elif not isinstance(value, (str, int, float, bool, type(None))):
                sanitized[key] = str(value)
            else:
                sanitized[key] = value
                
    return sanitized

def _load_context() -> Dict[str, Any]:
    """
    Load the persistent context from file.
    
    Returns:
        Dict[str, Any]: The persistent context data
    """
    try:
        if os.path.exists(CONTEXT_FILE):
            try:
                with open(CONTEXT_FILE, 'r') as f:
                    context = json.load(f)
                    
                    # Ensure the query_results field exists for backward compatibility
                    if "home_assistant" in context and "query_results" not in context["home_assistant"]:
                        context["home_assistant"]["query_results"] = {}
                        
                    return context
            except json.JSONDecodeError as e:
                logger.error(f"Error loading persistent context: {e}")
                logger.info("Creating backup of corrupted context file and using default context")
                
                # Create a backup of the corrupted file
                backup_file = f"{CONTEXT_FILE}.corrupted.{int(time.time())}"
                try:
                    import shutil
                    shutil.copy2(CONTEXT_FILE, backup_file)
                    logger.info(f"Created backup of corrupted context file: {backup_file}")
                except Exception as backup_error:
                    logger.error(f"Failed to create backup of corrupted context file: {backup_error}")
                
                # Return default context
                return DEFAULT_CONTEXT
        else:
            logger.info("No persistent context file found, creating default context")
            return DEFAULT_CONTEXT
    except Exception as e:
        logger.error(f"Error loading persistent context: {e}")
        return DEFAULT_CONTEXT

def _save_context(context: Dict[str, Any]) -> None:
    """
    Save the persistent context to file.
    
    Args:
        context (Dict[str, Any]): The context data to save
    """
    try:
        # Sanitize the entire context before saving
        sanitized_context = _sanitize_result(context)
        
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(sanitized_context, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
    except Exception as e:
        logger.error(f"Error saving persistent context: {e}")

def update_home_assistant_devices(devices: List[Dict[str, Any]]) -> None:
    """
    Update the Home Assistant devices in the persistent context.
    
    Args:
        devices (List[Dict[str, Any]]): List of Home Assistant devices
    """
    context = _load_context()
    
    # Group devices by domain for better organization
    devices_by_domain = {}
    for device in devices:
        entity_id = device.get('entity_id', '')
        if not entity_id:
            continue
            
        domain = entity_id.split('.')[0]
        friendly_name = device.get('attributes', {}).get('friendly_name', entity_id)
        state = device.get('state', 'unknown')
        
        if domain not in devices_by_domain:
            devices_by_domain[domain] = []
        
        devices_by_domain[domain].append({
            'entity_id': entity_id,
            'friendly_name': friendly_name,
            'state': state
        })
    
    context['home_assistant']['devices'] = devices_by_domain
    _save_context(context)
    logger.info(f"Updated Home Assistant devices in persistent context: {len(devices)} devices")

def update_home_assistant_services(services: Dict[str, Any]) -> None:
    """
    Update the Home Assistant services in the persistent context.
    
    Args:
        services (Dict[str, Any]): Dictionary of Home Assistant services by domain
    """
    context = _load_context()
    
    # Filter services to only include domains we have devices for
    filtered_services = {}
    device_domains = context['home_assistant']['devices'].keys()
    
    for domain, domain_services in services.items():
        if domain in device_domains:
            filtered_services[domain] = {}
            for service_name, service_data in domain_services.items():
                filtered_services[domain][service_name] = {
                    'description': service_data.get('description', 'No description'),
                    'fields': service_data.get('fields', {})
                }
    
    context['home_assistant']['services'] = filtered_services
    _save_context(context)
    logger.info(f"Updated Home Assistant services in persistent context")

def update_home_assistant_climate_devices(climate_devices: List[Dict[str, Any]]) -> None:
    """
    Update the Home Assistant climate devices in the persistent context.
    
    Args:
        climate_devices (List[Dict[str, Any]]): List of Home Assistant climate devices
    """
    context = _load_context()
    
    climate_info = []
    for device in climate_devices:
        entity_id = device.get('entity_id', '')
        friendly_name = device.get('attributes', {}).get('friendly_name', entity_id)
        
        climate_info.append({
            'entity_id': entity_id,
            'friendly_name': friendly_name,
            'current_temperature': device.get('attributes', {}).get('current_temperature'),
            'target_temperature': device.get('attributes', {}).get('temperature'),
            'hvac_mode': device.get('state'),
            'hvac_modes': device.get('attributes', {}).get('hvac_modes', []),
            'min_temp': device.get('attributes', {}).get('min_temp'),
            'max_temp': device.get('attributes', {}).get('max_temp')
        })
    
    context['home_assistant']['climate_devices'] = climate_info
    _save_context(context)
    logger.info(f"Updated Home Assistant climate devices in persistent context: {len(climate_devices)} devices")

def update_home_assistant_query_result(action_name: str, result: Dict[str, Any]) -> None:
    """
    Update the Home Assistant query result in the persistent context.
    
    Args:
        action_name (str): Name of the action that generated the result
        result (Dict[str, Any]): Result data from the action
    """
    context = _load_context()
    
    # Create a copy of the result to avoid modifying the original
    result_copy = result.copy() if result else {}
    
    # Sanitize the result to ensure it can be safely serialized
    result_copy = _sanitize_result(result_copy)
    
    # Limit the size of the full_weather data if present
    if action_name == "get_weather" and "full_weather" in result_copy:
        # Remove potentially large or unnecessary fields from full_weather
        if "last_changed" in result_copy["full_weather"]:
            del result_copy["full_weather"]["last_changed"]
        if "last_updated" in result_copy["full_weather"]:
            del result_copy["full_weather"]["last_updated"]
        # Keep only essential attributes
        if "attributes" in result_copy["full_weather"]:
            essential_attrs = ["temperature", "humidity", "pressure", "wind_speed", 
                              "wind_bearing", "temperature_unit", "friendly_name"]
            filtered_attrs = {k: v for k, v in result_copy["full_weather"]["attributes"].items() 
                             if k in essential_attrs}
            result_copy["full_weather"]["attributes"] = filtered_attrs
    
    # Limit the size of the full_state data for thermostat
    if action_name == "get_thermostat" and "full_state" in result_copy:
        # Remove potentially large or unnecessary fields from full_state
        if "last_changed" in result_copy["full_state"]:
            del result_copy["full_state"]["last_changed"]
        if "last_updated" in result_copy["full_state"]:
            del result_copy["full_state"]["last_updated"]
        # Keep only essential attributes
        if "attributes" in result_copy["full_state"]:
            essential_attrs = ["current_temperature", "temperature", "hvac_mode", "hvac_action", 
                              "min_temp", "max_temp", "friendly_name", "hvac_modes", "fan_mode", 
                              "preset_mode", "supported_features"]
            filtered_attrs = {k: v for k, v in result_copy["full_state"]["attributes"].items() 
                             if k in essential_attrs}
            result_copy["full_state"]["attributes"] = filtered_attrs
            
        # Explicitly convert any datetime objects to strings
        for key, value in list(result_copy["full_state"].items()):
            if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
                result_copy["full_state"][key] = value.isoformat()
    
    # Add timestamp to the result
    result_with_timestamp = {
        "timestamp": time.time(),
        "result": result_copy
    }
    
    # Update the query result in the context
    context['home_assistant']['query_results'][action_name] = result_with_timestamp
    
    # Save the updated context
    _save_context(context)
    logger.info(f"Updated Home Assistant query result for action '{action_name}' in persistent context")

def get_context_for_llm() -> str:
    """
    Get the persistent context formatted as a string for the LLM.
    
    Returns:
        str: The formatted context string
    """
    try:
        context = _load_context()
        
        # Format the context as a string
        context_str = "# Home Assistant Smart Home Information\n\n"
        
        # Add recent query results if available
        query_results = context.get('home_assistant', {}).get('query_results', {})
        if query_results:
            context_str += "## Recent Home Assistant Query Results\n\n"
            
            for action_name, result_data in query_results.items():
                try:
                    # Skip if result_data is not properly formatted
                    if not isinstance(result_data, dict):
                        logger.warning(f"Skipping malformed result data for {action_name}: {result_data}")
                        continue
                        
                    result = result_data.get('result', {})
                    if not result:
                        logger.warning(f"Empty result for {action_name}")
                        continue
                        
                    message = result.get('message', '')
                    
                    if message:
                        context_str += f"### {action_name.replace('_', ' ').title()} Result:\n"
                        context_str += f"{message}\n"
                        
                        # Add additional details based on action type
                        if action_name == 'get_thermostat':
                            entity_id = result.get('entity_id', '')
                            current_temp = result.get('current_temperature', '')
                            target_temp = result.get('target_temperature', '')
                            mode = result.get('hvac_mode', '')
                            action = result.get('hvac_action', '')
                            
                            if entity_id:
                                context_str += f"Entity: {entity_id}\n"
                            if current_temp:
                                context_str += f"Current Temperature: {current_temp}°F\n"
                            if target_temp:
                                context_str += f"Target Temperature: {target_temp}°F\n"
                            if mode:
                                context_str += f"Mode: {mode}\n"
                            if action:
                                context_str += f"Action: {action}\n"
                        
                        elif action_name == 'get_weather':
                            temperature = result.get('temperature', '')
                            humidity = result.get('humidity', '')
                            pressure = result.get('pressure', '')
                            wind_speed = result.get('wind_speed', '')
                            state = result.get('state', '')
                            
                            # Explicitly add weather condition information
                            context_str += "Weather information:\n"
                            
                            if state:
                                context_str += f"Condition: {state}\n"
                            if temperature:
                                context_str += f"Temperature: {temperature}°F\n"
                            if humidity:
                                context_str += f"Humidity: {humidity}%\n"
                            if pressure:
                                context_str += f"Pressure: {pressure} hPa\n"
                            if wind_speed:
                                context_str += f"Wind Speed: {wind_speed} mph\n"
                                
                            # Add information about precipitation/rain if available
                            if state and state.lower() in ['rainy', 'pouring', 'raining']:
                                context_str += "It is currently raining.\n"
                            elif state and state.lower() in ['clear', 'sunny', 'partlycloudy', 'partly_cloudy', 'cloudy', 'fog', 'foggy']:
                                context_str += "It is not currently raining.\n"
                        
                        elif action_name == 'list_climate_devices':
                            devices = result.get('devices', [])
                            count = result.get('count', 0)
                            
                            if count > 0:
                                context_str += f"Found {count} climate devices:\n"
                                for device in devices:
                                    friendly_name = device.get('friendly_name', device.get('entity_id', ''))
                                    current_temp = device.get('current_temperature', '')
                                    target_temp = device.get('target_temperature', '')
                                    hvac_mode = device.get('hvac_mode', '')
                                    
                                    context_str += f"- {friendly_name}: Currently {current_temp}°F, set to {target_temp}°F in {hvac_mode} mode\n"
                        
                        elif action_name == 'get_smart_devices':
                            domains = result.get('domains', {})
                            count = result.get('count', 0)
                            
                            if count > 0:
                                context_str += f"Found {count} smart devices across {len(domains)} domains:\n"
                                for domain, domain_devices in domains.items():
                                    context_str += f"- {domain.capitalize()} ({len(domain_devices)})\n"
                                    for device in domain_devices[:5]:  # Limit to 5 devices per domain
                                        friendly_name = device.get('friendly_name', device.get('entity_id', ''))
                                        state = device.get('state', '')
                                        context_str += f"  - {friendly_name}: {state}\n"
                                    if len(domain_devices) > 5:
                                        context_str += f"  - ... and {len(domain_devices) - 5} more {domain} devices\n"
                        
                        context_str += "\n"
                except Exception as action_error:
                    logger.error(f"Error processing {action_name} result: {action_error}")
                    continue
        
        # Add climate devices if available
        climate_devices = context.get('home_assistant', {}).get('climate_devices', [])
        if climate_devices:
            context_str += "## Climate Devices\n\n"
            for device in climate_devices:
                entity_id = device.get('entity_id', '')
                attributes = device.get('attributes', {})
                friendly_name = attributes.get('friendly_name', entity_id)
                current_temp = attributes.get('current_temperature', '')
                target_temp = attributes.get('temperature', '')
                hvac_mode = attributes.get('hvac_mode', '')
                
                context_str += f"- {friendly_name}: Currently {current_temp}°F, set to {target_temp}°F in {hvac_mode} mode\n"
            
            context_str += "\n"
        
        return context_str
    except Exception as e:
        logger.error(f"Error formatting context for LLM: {e}")
        return "# Home Assistant Smart Home Information\n\nError retrieving context data.\n"

def clear_context() -> None:
    """
    Clear the persistent context and reset to default.
    """
    try:
        _save_context(DEFAULT_CONTEXT)
        logger.info("Cleared persistent context")
    except Exception as e:
        logger.error(f"Error clearing persistent context: {e}")
