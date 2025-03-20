"""
windows_apps.py - Provides mapping between friendly app names and Windows executable names.
"""

import os
import logging
import re
from typing import Dict, Optional
from dotenv import load_dotenv

# Import the logger configuration
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Dictionary mapping friendly app names to their Windows executable names
# This includes both built-in Windows apps and common third-party applications
APP_MAPPING: Dict[str, str] = {
    # Windows built-in apps
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "settings": "ms-settings:",
    "word pad": "wordpad.exe",
    "wordpad": "wordpad.exe",
    "character map": "charmap.exe",
    "snipping tool": "snippingtool.exe",
    "photos": "ms-photos:",
    "camera": "microsoft.windows.camera:",
    "calendar": "outlookcal:",
    "clock": "ms-clock:",
    "mail": "outlookmail:",
    "maps": "bingmaps:",
    "store": "ms-windows-store:",
    "microsoft store": "ms-windows-store:",
    "weather": "bingweather:",
    "xbox": "xboxapp:",
    
    # Common browsers
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "mozilla firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "internet explorer": "iexplore.exe",
    "opera": "opera.exe",
    "brave": "brave.exe",
    
    # Common applications
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "slack": "slack.exe",
    "zoom": "zoom.exe",
    "teams": "teams.exe",
    "microsoft teams": "teams.exe",
    "visual studio code": "code.exe",
    "vs code": "code.exe",
    "code": "code.exe",
    "visual studio": "devenv.exe",
    "excel": "excel.exe",
    "microsoft excel": "excel.exe",
    "word": "winword.exe",
    "microsoft word": "winword.exe",
    "powerpoint": "powerpnt.exe",
    "microsoft powerpoint": "powerpnt.exe",
    "outlook": "outlook.exe",
    "microsoft outlook": "outlook.exe",
    "adobe reader": "acrord32.exe",
    "acrobat reader": "acrord32.exe",
    "photoshop": "photoshop.exe",
    "adobe photoshop": "photoshop.exe",
    "illustrator": "illustrator.exe",
    "adobe illustrator": "illustrator.exe",
    "steam": "steam.exe",
    "vlc": "vlc.exe",
    "vlc media player": "vlc.exe",
    "winamp": "winamp.exe",
    "itunes": "itunes.exe",
    "7zip": "7zfm.exe",
    "7-zip": "7zfm.exe",
    "winrar": "winrar.exe",
    "skype": "skype.exe",
    "obs": "obs64.exe",
    "obs studio": "obs64.exe",
    "quicktime": "quicktimeplayer.exe",
    "quicktime player": "quicktimeplayer.exe"
}

# Load custom app mappings from environment variables
def load_custom_app_mappings():
    """
    Load custom app mappings from environment variables.
    
    Format in .env file should be:
    APP_MAPPING_<friendly_name>=<executable_path>
    
    Example:
    APP_MAPPING_discord=C:\\Users\\username\\AppData\\Local\\Discord\\app-1.0.9003\\Discord.exe
    APP_MAPPING_spotify=C:\\Program Files\\Spotify\\Spotify.exe
    """
    custom_mappings = {}
    
    # Look for environment variables with the APP_MAPPING_ prefix
    for key, value in os.environ.items():
        if key.startswith('APP_MAPPING_'):
            # Extract the friendly name (convert to lowercase for consistency)
            friendly_name = key[len('APP_MAPPING_'):].lower()
            
            # Add to custom mappings
            if friendly_name and value:
                custom_mappings[friendly_name] = value
                logger.info(f"Loaded custom app mapping: {friendly_name} -> {value}")
    
    return custom_mappings

# Apply custom mappings from .env file
custom_mappings = load_custom_app_mappings()
APP_MAPPING.update(custom_mappings)

def get_app_executable(app_name: str) -> Optional[str]:
    """
    Get the executable name for a given app friendly name.
    
    Args:
        app_name: Friendly name of the app (case-insensitive)
        
    Returns:
        The executable name if found, None otherwise
    """
    # Convert to lowercase for case-insensitive matching
    app_name_lower = app_name.lower()
    
    # Direct match in the mapping
    if app_name_lower in APP_MAPPING:
        return APP_MAPPING[app_name_lower]
    
    # Check if any key contains the app name as a substring
    for key, value in APP_MAPPING.items():
        if app_name_lower in key or key in app_name_lower:
            logger.info(f"Fuzzy matched '{app_name}' to '{key}' -> '{value}'")
            return value
    
    # If no match found, return the original name
    # This allows for direct executable names or full paths
    logger.info(f"No mapping found for '{app_name}', using as-is")
    return app_name

def list_available_apps() -> list:
    """
    Get a list of all available app friendly names.
    
    Returns:
        List of friendly app names that can be opened
    """
    return sorted(APP_MAPPING.keys())
