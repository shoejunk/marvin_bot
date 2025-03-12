"""
Home Assistant integration module for Marvin.

This module provides functionality to interact with Home Assistant,
allowing Marvin to control smart home devices like the Resideo Honeywell AC.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from homeassistant_api import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class HomeAssistantController:
    """Controller class for interacting with Home Assistant."""
    
    def __init__(self, api_url: str = None, token: str = None):
        """
        Initialize the Home Assistant controller.
        
        Args:
            api_url: The URL to the Home Assistant API (e.g., "http://localhost:8123/api")
                     If None, will use the HOME_ASSISTANT_URL environment variable
            token: The long-lived access token for Home Assistant
                   If None, will use the HOME_ASSISTANT_TOKEN environment variable
        """
        # Use provided values or fall back to environment variables
        self.api_url = api_url or os.getenv('HOME_ASSISTANT_URL')
        self.token = token or os.getenv('HOME_ASSISTANT_TOKEN')
        self.client = None
        self.connected = False
    
    def connect(self) -> bool:
        """
        Connect to the Home Assistant instance.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            self.client = Client(self.api_url, self.token)
            self.connected = True
            logger.info("Successfully connected to Home Assistant")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Home Assistant: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the Home Assistant instance."""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Disconnected from Home Assistant")
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get a list of all devices from Home Assistant.
        
        Returns:
            List[Dict[str, Any]]: List of device information
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return []
        
        try:
            states = self.client.get_states()
            return [state.dict() for state in states]
        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            return []
    
    def get_climate_devices(self) -> List[Dict[str, Any]]:
        """
        Get a list of climate devices (thermostats) from Home Assistant.
        
        Returns:
            List[Dict[str, Any]]: List of climate device information
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return []
        
        try:
            states = self.client.get_states()
            climate_devices = [state.dict() for state in states if state.entity_id.startswith("climate.")]
            return climate_devices
        except Exception as e:
            logger.error(f"Failed to get climate devices: {e}")
            return []
    
    def set_thermostat_temperature(self, entity_id: str, temperature: float, mode: str = "heat") -> bool:
        """
        Set the temperature for a thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat (e.g., "climate.living_room")
            temperature: The temperature to set
            mode: The HVAC mode ("heat", "cool", "heat_cool", or "off")
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return False
        
        try:
            climate = self.client.get_domain("climate")
            
            if mode == "heat":
                climate.set_temperature(entity_id=entity_id, temperature=temperature, hvac_mode="heat")
            elif mode == "cool":
                climate.set_temperature(entity_id=entity_id, temperature=temperature, hvac_mode="cool")
            elif mode == "heat_cool":
                climate.set_temperature(entity_id=entity_id, temperature=temperature, hvac_mode="heat_cool")
            else:
                logger.error(f"Unsupported HVAC mode: {mode}")
                return False
                
            logger.info(f"Set {entity_id} to {temperature} degrees in {mode} mode")
            return True
        except Exception as e:
            logger.error(f"Failed to set thermostat temperature: {e}")
            return False
    
    def set_hvac_mode(self, entity_id: str, mode: str) -> bool:
        """
        Set the HVAC mode for a thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat (e.g., "climate.living_room")
            mode: The HVAC mode ("heat", "cool", "heat_cool", or "off")
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return False
        
        try:
            climate = self.client.get_domain("climate")
            
            if mode == "off":
                climate.turn_off(entity_id=entity_id)
            else:
                climate.set_hvac_mode(entity_id=entity_id, hvac_mode=mode)
                
            logger.info(f"Set {entity_id} to {mode} mode")
            return True
        except Exception as e:
            logger.error(f"Failed to set HVAC mode: {e}")
            return False
    
    def get_thermostat_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat (e.g., "climate.living_room")
            
        Returns:
            Optional[Dict[str, Any]]: The thermostat state or None if not found
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return None
        
        try:
            # Get all states and filter for the one we want
            # This avoids the error: RawClient.get_state() takes 1 positional argument but 2 were given
            states = self.client.get_states()
            for state in states:
                if state.entity_id == entity_id:
                    return state.dict()
            
            logger.error(f"Entity {entity_id} not found in states")
            return None
        except Exception as e:
            logger.error(f"Failed to get thermostat state: {e}")
            return None
            
    def get_weather(self, entity_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get weather information from Home Assistant.
        
        Args:
            entity_id: The entity ID of the weather entity (e.g., "weather.home")
                       If None, will return the first weather entity found
            
        Returns:
            Optional[Dict[str, Any]]: The weather information or None if not found
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return None
        
        try:
            # Get all states
            states = self.client.get_states()
            
            # If entity_id is provided, find that specific entity
            if entity_id:
                for state in states:
                    if state.entity_id == entity_id:
                        return state.dict()
                logger.error(f"Weather entity {entity_id} not found in states")
                return None
            
            # Otherwise, find the first weather entity
            for state in states:
                if state.entity_id.startswith("weather."):
                    return state.dict()
            
            logger.error("No weather entities found in states")
            return None
        except Exception as e:
            logger.error(f"Failed to get weather information: {e}")
            return None
    
    def get_weather_entities(self) -> List[Dict[str, Any]]:
        """
        Get a list of all weather entities from Home Assistant.
        
        Returns:
            List[Dict[str, Any]]: List of weather entity information
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return []
        
        try:
            states = self.client.get_states()
            weather_entities = [state.dict() for state in states if state.entity_id.startswith("weather.")]
            return weather_entities
        except Exception as e:
            logger.error(f"Failed to get weather entities: {e}")
            return []


# Example usage
if __name__ == "__main__":
    # This would typically come from environment variables or settings
    ha_controller = HomeAssistantController()
    if ha_controller.connect():
        # Get all climate devices
        climate_devices = ha_controller.get_climate_devices()
        print(f"Found {len(climate_devices)} climate devices")
        
        # Example: Set temperature for the first climate device
        if climate_devices:
            entity_id = climate_devices[0]["entity_id"]
            ha_controller.set_thermostat_temperature(entity_id, 72, "cool")
        
        ha_controller.disconnect()
