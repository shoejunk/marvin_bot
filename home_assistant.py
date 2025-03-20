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

    def set_thermostat_temperature(self, entity_id: str, temperature: float) -> bool:
        """
        Set the temperature for a thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat (e.g., "climate.living_room")
            temperature: The temperature to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug(f"Setting {entity_id} to {temperature} degrees")
        
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return False
        
        try:
            climate = self.client.get_domain("climate")
            
            # Set the temperature
            logger.info(f"Setting temperature to {temperature} for {entity_id}")
            climate.set_temperature(entity_id=entity_id, temperature=temperature)
            
            logger.info(f"Successfully set {entity_id} to {temperature} degrees")
            return True
        except Exception as e:
            logger.error(f"Failed to set thermostat temperature: {e}")
            return False
    
    def set_thermostat_mode(self, entity_id: str, mode: str) -> bool:
        """
        Set the HVAC mode for a thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat (e.g., "climate.living_room")
            mode: The HVAC mode ("heat", "cool", "heat_cool", or "off")
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug(f"Setting {entity_id} to {mode} mode")
        
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return False
        
        try:
            climate = self.client.get_domain("climate")
            
            # First set the HVAC mode
            if mode in ["heat", "cool", "heat_cool", "off"]:
                logger.info(f"Setting HVAC mode to {mode} for {entity_id}")
                # Use set_hvac_mode method to explicitly set the mode first
                climate.set_hvac_mode(entity_id=entity_id, hvac_mode=mode)
            else:
                logger.error(f"Unsupported HVAC mode: {mode}")
                return False
            
            logger.info(f"Successfully set {entity_id} to {mode} mode")
            return True
        except Exception as e:
            logger.error(f"Failed to set thermostat mode: {e}")
            return False
    
    def set_thermostat_temperature_and_mode(self, entity_id: str, temperature: float, mode: str = "heat") -> bool:
        """
        Set the temperature and mode for a thermostat.
        
        Args:
            entity_id: The entity ID of the thermostat (e.g., "climate.living_room")
            temperature: The temperature to set
            mode: The HVAC mode ("heat", "cool", "heat_cool", or "off")
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug(f"Setting {entity_id} to {temperature} degrees in {mode} mode")
        
        set_thermostat_temperature(entity_id, temperature)
        set_thermostat_mode(entity_id, mode)
            
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
            
    def control_entity(self, entity_id: str, service: str, **service_data) -> bool:
        """
        Generic method to control any entity in Home Assistant.
        
        Args:
            entity_id: The entity ID to control (e.g., "light.living_room")
            service: The service to call (e.g., "turn_on", "turn_off", "toggle")
            **service_data: Additional service data parameters
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return False
            
        try:
            # Extract the domain from the entity_id
            if '.' not in entity_id:
                logger.error(f"Invalid entity_id format: {entity_id}")
                return False
                
            domain = entity_id.split('.')[0]
            
            # Get the domain object
            domain_obj = self.client.get_domain(domain)
            
            # Prepare service data (excluding entity_id as it's passed separately)
            service_data_copy = service_data.copy()
            
            # Call the appropriate method on the domain object
            logger.info(f"Calling service {domain}.{service} with entity_id: {entity_id} and data: {service_data}")
            
            # Most domain objects have methods like turn_on, turn_off, toggle, etc.
            if hasattr(domain_obj, service):
                method = getattr(domain_obj, service)
                try:
                    # Set a timeout for the operation
                    import asyncio
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(method, entity_id=entity_id, **service_data_copy)
                        # Wait for 10 seconds max
                        result = future.result(timeout=10)
                except TimeoutError:
                    logger.error(f"Timeout while controlling {entity_id} with service {service}")
                    return False
            else:
                # For services that don't match method names directly
                logger.warning(f"Method {service} not found on domain {domain}, trying generic approach")
                try:
                    # Set a timeout for the operation
                    import asyncio
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor() as executor:
                        if service == "turn_on":
                            future = executor.submit(domain_obj.turn_on, entity_id=entity_id, **service_data_copy)
                        elif service == "turn_off":
                            future = executor.submit(domain_obj.turn_off, entity_id=entity_id, **service_data_copy)
                        elif service == "toggle":
                            future = executor.submit(domain_obj.toggle, entity_id=entity_id, **service_data_copy)
                        else:
                            logger.error(f"Unsupported service: {service} for domain {domain}")
                            return False
                        # Wait for 10 seconds max
                        result = future.result(timeout=10)
                except TimeoutError:
                    logger.error(f"Timeout while controlling {entity_id} with service {service}")
                    return False
            
            logger.info(f"Successfully controlled {entity_id} with service {service}")
            return True
        except Exception as e:
            logger.error(f"Failed to control entity {entity_id} with service {service}: {e}")
            return False
    
    def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of any entity.
        
        Args:
            entity_id: The entity ID (e.g., "light.living_room")
            
        Returns:
            Optional[Dict[str, Any]]: The entity state or None if not found
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return None
        
        try:
            # Get all states and filter for the one we want
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            try:
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(self.client.get_states)
                    # Wait for 10 seconds max
                    states = future.result(timeout=10)
                    
                    for state in states:
                        if state.entity_id == entity_id:
                            return state.dict()
                
                logger.error(f"Entity {entity_id} not found in states")
                return None
            except TimeoutError:
                logger.error(f"Timeout while getting states for entity {entity_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get entity state: {e}")
            return None
            
    def get_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available services from Home Assistant.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of services by domain
        """
        if not self.connected or not self.client:
            logger.error("Not connected to Home Assistant")
            return {}
        
        try:
            services = self.client.get_services()
            # Convert to a more usable dictionary format
            services_dict = {}
            for domain, domain_services in services.items():
                services_dict[domain] = {}
                for service_name, service_data in domain_services.items():
                    services_dict[domain][service_name] = service_data
            
            logger.info(f"Retrieved {sum(len(domain_services) for domain_services in services_dict.values())} services from Home Assistant")
            return services_dict
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return {}


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
