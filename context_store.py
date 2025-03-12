#!/usr/bin/env python3
"""
context_store.py - Manages persistent context data for the LLM.
This module provides storage for information that should be included with every LLM call,
regardless of conversation history limits.
"""

import json
import os
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
        "climate_devices": []
    },
    "system": {}
}

def _load_context() -> Dict[str, Any]:
    """
    Load the persistent context from file.
    
    Returns:
        Dict[str, Any]: The persistent context data
    """
    try:
        if os.path.exists(CONTEXT_FILE):
            with open(CONTEXT_FILE, 'r') as f:
                return json.load(f)
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
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(context, f, indent=2)
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

def get_context_for_llm() -> str:
    """
    Get the persistent context formatted as a string for the LLM.
    
    Returns:
        str: The formatted context string
    """
    context = _load_context()
    
    # Format Home Assistant devices information
    context_str = "# Home Assistant Smart Home Information\n\n"
    
    # Add climate devices with detailed information
    if context['home_assistant']['climate_devices']:
        context_str += "## Climate Devices\n"
        for device in context['home_assistant']['climate_devices']:
            context_str += f"- {device['friendly_name']} ({device['entity_id']})\n"
            context_str += f"  * Current temperature: {device['current_temperature']}\n"
            context_str += f"  * Target temperature: {device['target_temperature']}\n"
            context_str += f"  * Mode: {device['hvac_mode']}\n"
            context_str += f"  * Available modes: {', '.join(device['hvac_modes'])}\n"
            context_str += f"  * Temperature range: {device['min_temp']} - {device['max_temp']}\n"
        context_str += "\n"
    
    # Add other devices by domain
    if context['home_assistant']['devices']:
        context_str += "## Smart Home Devices\n"
        for domain, devices in context['home_assistant']['devices'].items():
            context_str += f"\n### {domain.upper()} devices:\n"
            for device in devices:
                context_str += f"- {device['friendly_name']}: {device['entity_id']} (current state: {device['state']})\n"
        context_str += "\n"
    
    # Add services information
    if context['home_assistant']['services']:
        context_str += "## Available Home Assistant Services\n"
        for domain, services in context['home_assistant']['services'].items():
            context_str += f"\n### {domain.upper()} services:\n"
            for service_name, service_data in services.items():
                context_str += f"- {service_name}: {service_data['description']}\n"
                
                # Include service fields/parameters if available
                fields = service_data.get('fields', {})
                if fields:
                    context_str += "  Parameters:\n"
                    for field_name, field_data in fields.items():
                        field_desc = field_data.get('description', 'No description')
                        context_str += f"    - {field_name}: {field_desc}\n"
    
    return context_str

def clear_context() -> None:
    """
    Clear the persistent context and reset to default.
    """
    _save_context(DEFAULT_CONTEXT)
    logger.info("Cleared persistent context")
