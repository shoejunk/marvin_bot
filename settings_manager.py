"""
settings_manager.py - Manages loading and saving application settings.
Provides functions to read from and write to the settings.json file.
"""

import os
import json
import logging
from logger_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Path to the settings file
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')

# Default settings
DEFAULT_SETTINGS = {
    "wake_word_required": True
}

def load_settings():
    """
    Load settings from the settings.json file.
    If the file doesn't exist or is invalid, return default settings.
    
    Returns:
        dict: The loaded settings or default settings
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                logger.info(f"Settings loaded successfully: {settings}")
                return settings
        else:
            logger.warning(f"Settings file not found at {SETTINGS_FILE}, using defaults")
            # Create the settings file with default values
            save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS

def save_settings(settings):
    """
    Save settings to the settings.json file.
    
    Args:
        settings (dict): The settings to save
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
            logger.info(f"Settings saved successfully: {settings}")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

def update_setting(key, value):
    """
    Update a single setting and save to file.
    
    Args:
        key (str): The setting key to update
        value: The new value for the setting
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        settings = load_settings()
        settings[key] = value
        return save_settings(settings)
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        return False
