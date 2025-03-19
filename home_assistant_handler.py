"""
Home Assistant handler module for Marvin.

This module handles Home Assistant related actions and integrates with Marvin's
conversation flow to control smart home devices like the Resideo Honeywell AC.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from home_assistant import HomeAssistantController
from dotenv import load_dotenv
from settings_manager import get_active_personality

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class HomeAssistantHandler:
    """Handler class for Home Assistant actions in Marvin."""
    
    def __init__(self, settings: Dict[str, Any] = None):
        """
        Initialize the Home Assistant handler.
        
        Args:
            settings: Dictionary containing Marvin settings (optional)
        """
        self.settings = settings or {}
        self.controller = None
        self.speak_function = None
        self.display = None
        self.update_history = None
        
        # Initialize the controller using environment variables
        self.controller = HomeAssistantController()
        self.connect()
    
    def set_dependencies(self, speak_function, display, update_history):
        """
        Set dependencies needed for user interaction.
        
        Args:
            speak_function: Function to speak text responses
            display: Display interface for UI updates
            update_history_function: Function to update conversation history
        """
        self.speak_function = speak_function
        self.display = display
        self.update_history = update_history
        
    def _store_result_in_context(self, action_name, result):
        """
        Store the result of an action in the persistent context.
        
        Args:
            action_name: Name of the action
            result: Result data to store
        """
        try:
            # Import here to avoid circular imports
            from context_store import update_home_assistant_query_result
            update_home_assistant_query_result(action_name, result)
        except Exception as e:
            logger.error(f"Error storing result in context: {e}")
            
    def connect(self) -> bool:
        """
        Connect to Home Assistant.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        if not self.controller:
            logger.error("Home Assistant controller not initialized")
            return False
            
        return self.controller.connect()
    
    def disconnect(self) -> None:
        """Disconnect from Home Assistant."""
        if self.controller:
            self.controller.disconnect()
    
    async def handle_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a Home Assistant related action.
        
        Args:
            action: The action to perform
            parameters: Parameters for the action
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        if not self.controller:
            return {"success": False, "message": "Home Assistant not configured"}
            
        if not self.controller.connected:
            connected = self.connect()
            if not connected:
                return {"success": False, "message": "Failed to connect to Home Assistant"}
        
        # Set a timeout for the entire action
        import asyncio
        try:
            # Create a task for the action and wait for it with a timeout
            action_task = asyncio.create_task(self._execute_action(action, parameters))
            # Wait for 15 seconds max
            return await asyncio.wait_for(action_task, timeout=15)
        except asyncio.TimeoutError:
            logger.error(f"Timeout while executing Home Assistant action: {action}")
            # If the action timed out, we should speak to the user
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(f"I'm sorry, the Home Assistant action {action} timed out. Please try again later.", 
                                         personality_name=active_personality)
            return {"success": False, "message": f"Action {action} timed out"}
    
    async def _execute_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Home Assistant action with the given parameters.
        
        Args:
            action: The action to perform
            parameters: Parameters for the action
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        # Handle different actions
        if action == "set_thermostat":
            return await self.set_thermostat(parameters)
        elif action == "get_thermostat":
            return await self.get_thermostat(parameters)
        elif action == "turn_off_thermostat":
            return await self.turn_off_thermostat(parameters)
        elif action == "set_hvac_mode":
            return await self.set_hvac_mode(parameters)
        elif action == "list_climate_devices":
            return await self.list_climate_devices()
        elif action == "get_smart_devices":
            return await self.get_smart_devices()
        elif action == "get_weather":
            return await self.get_weather(parameters)
        elif action == "control_entity":
            return await self.control_entity(parameters)
        else:
            return {"success": False, "message": f"Unknown action: {action}"}
    
    async def set_thermostat(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle setting thermostat temperature.
        
        Args:
            parameters: Must contain 'entity_id', 'temperature', and optionally 'mode'
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        entity_id = parameters.get('entity_id')
        temperature = parameters.get('temperature')
        mode = parameters.get('mode', 'heat')
        
        if not entity_id or not temperature:
            message = "Missing required parameters: entity_id or temperature"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
        
        # Try to convert temperature to float if it's a string
        if isinstance(temperature, str):
            try:
                temperature = float(temperature)
            except ValueError:
                message = f"Invalid temperature value: {temperature}"
                if self.speak_function:
                    active_personality = get_active_personality()
                    await self.speak_function(message, personality_name=active_personality)
                return {"success": False, "message": message}
        
        # Set the thermostat
        success = self.controller.set_temperature(entity_id, temperature, mode)
        
        if success:
            message = f"Set {entity_id} to {temperature}°F in {mode} mode"
            
            # Store the result in context instead of speaking it
            result = {
                "success": True, 
                "message": message,
                "entity_id": entity_id,
                "temperature": temperature,
                "mode": mode
            }
            self._store_result_in_context("set_thermostat", result)
            
            return result
        else:
            message = f"Failed to set {entity_id} to {temperature}°F"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
    
    async def get_thermostat(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle getting thermostat information.
        
        Args:
            parameters: Must contain 'entity_id'
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        entity_id = parameters.get('entity_id')
        
        if not entity_id:
            message = "Missing required parameter: entity_id"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
        
        # Get the thermostat state
        state = self.controller.get_thermostat_state(entity_id)
        
        if state:
            # Extract relevant information
            attributes = state.get('attributes', {})
            current_temp = attributes.get('current_temperature')
            target_temp = attributes.get('temperature')
            hvac_mode = attributes.get('hvac_mode')
            hvac_action = attributes.get('hvac_action')
            friendly_name = attributes.get('friendly_name', entity_id)
            
            # Create a readable message
            message = f"{friendly_name} is currently {current_temp}°F"
            if target_temp:
                message += f", set to {target_temp}°F"
            if hvac_mode:
                message += f" in {hvac_mode} mode"
            if hvac_action:
                message += f" ({hvac_action})"
            
            # Store the result in context instead of speaking it
            result = {
                "success": True,
                "entity_id": entity_id,
                "current_temperature": current_temp,
                "target_temperature": target_temp,
                "hvac_mode": hvac_mode,
                "hvac_action": hvac_action,
                "state": state.get('state'),
                "message": message,
                "full_state": state
            }
            self._store_result_in_context("get_thermostat", result)
            
            return result
        else:
            message = f"Failed to get state for {entity_id}"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
    
    async def turn_off_thermostat(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle turning off a thermostat.
        
        Args:
            parameters: Must contain 'entity_id'
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        entity_id = parameters.get('entity_id')
        
        if not entity_id:
            message = "Missing required parameter: entity_id"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
        
        success = self.controller.set_hvac_mode(entity_id, "off")
        
        if success:
            message = f"Turned off {entity_id}"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            if self.display:
                self.display.add_conversation(message, speaker='assistant')
            if self.update_history:
                self.update_history(message, "")
            return {"success": True, "message": message}
        else:
            message = f"Failed to turn off {entity_id}"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
    
    async def set_hvac_mode(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle setting HVAC mode.
        
        Args:
            parameters: Must contain 'entity_id' and 'mode'
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        entity_id = parameters.get('entity_id')
        mode = parameters.get('mode')
        
        if not entity_id or not mode:
            message = "Missing required parameters: entity_id or mode"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
        
        success = self.controller.set_hvac_mode(entity_id, mode)
        
        if success:
            message = f"Set {entity_id} to {mode} mode"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            if self.display:
                self.display.add_conversation(message, speaker='assistant')
            if self.update_history:
                self.update_history(message, "")
            return {"success": True, "message": message}
        else:
            message = f"Failed to set {entity_id} to {mode} mode"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
    
    async def list_climate_devices(self) -> Dict[str, Any]:
        """
        Handle listing all climate devices.
        
        Returns:
            Dict[str, Any]: Result of the action with list of climate devices
        """
        devices = self.controller.get_climate_devices()
        
        if devices:
            # Extract relevant information for a more readable response
            simplified_devices = []
            for device in devices:
                entity_id = device.get('entity_id')
                attributes = device.get('attributes', {})
                simplified_devices.append({
                    "entity_id": entity_id,
                    "friendly_name": attributes.get('friendly_name'),
                    "current_temperature": attributes.get('current_temperature'),
                    "target_temperature": attributes.get('temperature'),
                    "hvac_mode": attributes.get('hvac_mode'),
                    "hvac_action": attributes.get('hvac_action')
                })
            
            # Create a readable message
            message = f"Found {len(devices)} climate devices:\n"
            for device in simplified_devices:
                message += f"- {device['friendly_name'] or device['entity_id']}: " \
                          f"Currently {device['current_temperature']}°F, " \
                          f"set to {device['target_temperature']}°F in {device['hvac_mode']} mode\n"
            
            # Store the result in context instead of speaking it
            result = {
                "success": True,
                "count": len(devices),
                "devices": simplified_devices,
                "message": message,
                "full_devices": devices
            }
            self._store_result_in_context("list_climate_devices", result)
            
            return result
        else:
            message = "No climate devices found or failed to get devices"
            return {"success": False, "message": message}
    
    async def get_smart_devices(self) -> Dict[str, Any]:
        """
        Handle getting all smart devices.
        
        Returns:
            Dict[str, Any]: Result of the action with list of all devices
        """
        devices = self.controller.get_devices()
        
        if devices:
            # Group devices by domain
            domains = {}
            for device in devices:
                entity_id = device.get('entity_id', '')
                domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
                
                if domain not in domains:
                    domains[domain] = []
                
                domains[domain].append({
                    "entity_id": entity_id,
                    "friendly_name": device.get('attributes', {}).get('friendly_name'),
                    "state": device.get('state')
                })
            
            # Create a readable message
            message = f"Found {len(devices)} smart devices across {len(domains)} domains:\n"
            for domain, domain_devices in domains.items():
                message += f"\n{domain.capitalize()} ({len(domain_devices)}):\n"
                for device in domain_devices[:5]:  # Limit to 5 devices per domain to avoid too long messages
                    message += f"- {device['friendly_name'] or device['entity_id']}: {device['state']}\n"
                if len(domain_devices) > 5:
                    message += f"  ... and {len(domain_devices) - 5} more {domain} devices\n"
            
            # Store the result in context instead of speaking it
            result = {
                "success": True,
                "count": len(devices),
                "domains": domains,
                "message": message,
                "full_devices": devices
            }
            self._store_result_in_context("get_smart_devices", result)
            
            return result
        else:
            message = "No devices found or failed to get devices"
            return {"success": False, "message": message}
            
    async def get_weather(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle getting weather information.
        
        Args:
            parameters: May contain 'entity_id' for a specific weather entity
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        entity_id = parameters.get('entity_id', None)
        
        # Get weather information
        weather_info = self.controller.get_weather(entity_id)
        
        if weather_info:
            # Extract relevant information
            state = weather_info.get('state', 'unknown')
            attributes = weather_info.get('attributes', {})
            temperature = attributes.get('temperature')
            humidity = attributes.get('humidity')
            pressure = attributes.get('pressure')
            wind_speed = attributes.get('wind_speed')
            wind_bearing = attributes.get('wind_bearing')
            forecast = attributes.get('forecast', [])
            
            # Create a more detailed readable message
            message = f"Current weather is {state}"
            if temperature is not None:
                message += f", {temperature}°F"
            if humidity is not None:
                message += f", {humidity}% humidity"
            if pressure is not None:
                message += f", pressure {pressure} hPa"
            if wind_speed is not None:
                message += f", wind speed {wind_speed} mph"
                
            # Add forecast if available
            if forecast and len(forecast) > 0:
                tomorrow = forecast[0]
                message += f". Tomorrow: {tomorrow.get('condition', 'unknown')}, "
                message += f"high of {tomorrow.get('temperature', 'unknown')}°F, "
                message += f"low of {tomorrow.get('templow', 'unknown')}°F"
            
            # Store the result in context instead of speaking it
            result = {
                "success": True,
                "entity_id": weather_info.get('entity_id'),
                "state": state,
                "temperature": temperature,
                "humidity": humidity,
                "pressure": pressure,
                "wind_speed": wind_speed,
                "wind_bearing": wind_bearing,
                "forecast": forecast,
                "message": message,
                "full_weather": weather_info
            }
            
            # Log the result for debugging
            logger.info(f"Weather result: {result}")
            
            # Store in context
            self._store_result_in_context("get_weather", result)
            
            return result
        else:
            message = "Failed to get weather information"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
    
    async def control_entity(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle controlling a Home Assistant entity with a service.
        
        Args:
            parameters: Must contain 'entity_id' and 'service', may contain 'service_data'
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        entity_id = parameters.get('entity_id')
        service = parameters.get('service')
        service_data = parameters.get('service_data', {})
        
        if not entity_id or not service:
            message = "Missing required parameters: entity_id or service"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
        
        # Add entity_id to service_data if not already present
        if 'entity_id' not in service_data:
            service_data['entity_id'] = entity_id
            
        # Split service into domain.service_name if it contains a dot
        if '.' in service:
            domain, service_name = service.split('.', 1)
        else:
            # Try to determine domain from entity_id
            if '.' in entity_id:
                domain = entity_id.split('.', 1)[0]
                service_name = service
            else:
                message = f"Invalid service format: {service}. Must be in format domain.service_name"
                if self.speak_function:
                    active_personality = get_active_personality()
                    await self.speak_function(message, personality_name=active_personality)
                return {"success": False, "message": message}
        
        # Call the service
        success = self.controller.call_service(domain, service_name, service_data)
        
        if success:
            # Create a readable message
            friendly_name = self.controller.get_friendly_name(entity_id) or entity_id
            
            # Try to make a human-readable message based on the service
            if service_name == 'turn_on':
                message = f"Turned on {friendly_name}"
            elif service_name == 'turn_off':
                message = f"Turned off {friendly_name}"
            elif service_name == 'toggle':
                message = f"Toggled {friendly_name}"
            else:
                message = f"Called service {service} on {friendly_name}"
                
                # Add service data to message if present
                if service_data and len(service_data) > 1:  # More than just entity_id
                    data_str = ", ".join([f"{k}={v}" for k, v in service_data.items() if k != 'entity_id'])
                    message += f" with {data_str}"
            
            # Store the result in context instead of speaking it
            result = {
                "success": True,
                "message": message,
                "entity_id": entity_id,
                "service": service,
                "service_data": service_data
            }
            self._store_result_in_context("control_entity", result)
            
            return result
        else:
            message = f"Failed to call service {service} on {entity_id}"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}


# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Create handler
    handler = HomeAssistantHandler()
    
    async def main():
        # Example: List climate devices
        result = await handler.handle_action("list_climate_devices", {})
        print(json.dumps(result, indent=2))
        
        # Example: Set thermostat temperature
        if result["success"] and result["devices"]:
            entity_id = result["devices"][0]["entity_id"]
            set_result = await handler.handle_action("set_thermostat", {
                "entity_id": entity_id,
                "temperature": 72,
                "mode": "cool"
            })
            print(json.dumps(set_result, indent=2))
    
    # Run the async example
    asyncio.run(main())
    handler.disconnect()
