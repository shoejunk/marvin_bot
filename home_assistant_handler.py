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
        
        if not entity_id or temperature is None:
            message = "Missing required parameters: entity_id or temperature"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
        
        # Convert temperature to float if it's a string
        if isinstance(temperature, str):
            try:
                temperature = float(temperature)
            except ValueError:
                message = f"Invalid temperature value: {temperature}"
                if self.speak_function:
                    active_personality = get_active_personality()
                    await self.speak_function(message, personality_name=active_personality)
                return {"success": False, "message": message}
        
        success = self.controller.set_thermostat_temperature(entity_id, temperature, mode)
        
        if success:
            message = f"Set {entity_id} to {temperature} degrees in {mode} mode"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            if self.display:
                self.display.add_conversation(message, speaker='assistant')
            if self.update_history:
                self.update_history(message, "")
            return {
                "success": True, 
                "message": message
            }
        else:
            message = "Failed to set thermostat temperature"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
    
    async def get_thermostat(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle getting thermostat state.
        
        Args:
            parameters: Must contain 'entity_id'
            
        Returns:
            Dict[str, Any]: Result of the action with thermostat state
        """
        entity_id = parameters.get('entity_id')
        
        if not entity_id:
            message = "Missing required parameter: entity_id"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
        
        state = self.controller.get_thermostat_state(entity_id)
        
        if state:
            # Extract relevant information for a more readable response
            attributes = state.get('attributes', {})
            current_temp = attributes.get('current_temperature')
            target_temp = attributes.get('temperature')
            hvac_mode = attributes.get('hvac_mode')
            hvac_action = attributes.get('hvac_action')
            
            message = f"The {entity_id} is currently {hvac_action or 'idle'} in {hvac_mode} mode. " \
                     f"Current temperature is {current_temp}°F with target of {target_temp}°F."
            
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            if self.display:
                self.display.add_conversation(message, speaker='assistant')
            if self.update_history:
                self.update_history(message, "")
                
            return {
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
            
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            if self.display:
                self.display.add_conversation(message, speaker='assistant')
            if self.update_history:
                self.update_history(message, "")
                
            return {
                "success": True,
                "count": len(devices),
                "devices": simplified_devices,
                "message": message,
                "full_devices": devices
            }
        else:
            message = "No climate devices found or failed to get devices"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
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
            
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            if self.display:
                self.display.add_conversation(message, speaker='assistant')
            if self.update_history:
                self.update_history(message, "")
                
            return {
                "success": True,
                "count": len(devices),
                "domains": domains,
                "message": message,
                "full_devices": devices
            }
        else:
            message = "No devices found or failed to get devices"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
            
    async def get_weather(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle getting weather information.
        
        Args:
            parameters: May contain 'entity_id' for a specific weather entity
            
        Returns:
            Dict[str, Any]: Result of the action with weather information
        """
        entity_id = parameters.get('entity_id')
        
        # Get weather information
        weather_info = self.controller.get_weather(entity_id)
        
        if weather_info:
            # Extract relevant information for a more readable response
            attributes = weather_info.get('attributes', {})
            state = weather_info.get('state')  # Current condition (clear, cloudy, etc.)
            temperature = attributes.get('temperature')
            humidity = attributes.get('humidity')
            pressure = attributes.get('pressure')
            wind_speed = attributes.get('wind_speed')
            wind_bearing = attributes.get('wind_bearing')
            forecast = attributes.get('forecast', [])
            friendly_name = attributes.get('friendly_name', weather_info.get('entity_id'))
            
            # Create a readable message
            message = f"Current weather at {friendly_name}: {state}, {temperature}°F\n"
            message += f"Humidity: {humidity}%, Pressure: {pressure} hPa\n"
            message += f"Wind: {wind_speed} mph"
            if wind_bearing is not None:
                # Convert wind bearing to cardinal direction
                directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                index = round(wind_bearing / 45) % 8
                message += f" from the {directions[index]}"
            
            # Add forecast if available (just next day)
            if forecast and len(forecast) > 0:
                next_day = forecast[0]
                message += f"\n\nForecast for tomorrow: {next_day.get('condition')}, "
                message += f"High: {next_day.get('temperature')}°F, Low: {next_day.get('templow')}°F"
            
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            if self.display:
                self.display.add_conversation(message, speaker='assistant')
            if self.update_history:
                self.update_history(message, "")
                
            return {
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
        else:
            # If no specific entity was requested, try to list available weather entities
            if not entity_id:
                weather_entities = self.controller.get_weather_entities()
                if weather_entities:
                    entity_names = [entity.get('entity_id') for entity in weather_entities]
                    message = f"No default weather entity found. Available weather entities: {', '.join(entity_names)}"
                else:
                    message = "No weather entities found in Home Assistant"
            else:
                message = f"Failed to get weather information for {entity_id}"
                
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
    
    async def control_entity(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle controlling any entity in Home Assistant.
        
        Args:
            parameters: Must contain 'entity_id' and 'service', may contain additional service data
            
        Returns:
            Dict[str, Any]: Result of the action
        """
        entity_id = parameters.get('entity_id')
        service = parameters.get('service')
        
        if not entity_id or not service:
            message = "Missing required parameters: entity_id or service"
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            return {"success": False, "message": message}
        
        # Extract any additional service data
        service_data = {k: v for k, v in parameters.items() if k not in ['entity_id', 'service']}
        
        # Get current state before the action
        current_state = self.controller.get_entity_state(entity_id)
        
        # Call the service
        success = self.controller.control_entity(entity_id, service, **service_data)
        
        if success:
            # Get the entity type from the entity_id
            entity_type = entity_id.split('.')[0] if '.' in entity_id else 'entity'
            
            # Get friendly name if available
            friendly_name = None
            if current_state and 'attributes' in current_state:
                friendly_name = current_state['attributes'].get('friendly_name')
            
            display_name = friendly_name or entity_id
            
            # Create a message based on the service
            if service == 'turn_on':
                message = f"Turned on {display_name}"
            elif service == 'turn_off':
                message = f"Turned off {display_name}"
            elif service == 'toggle':
                message = f"Toggled {display_name}"
            else:
                # For other services, include the service name and any parameters
                message = f"Called service '{service}' on {display_name}"
                if service_data:
                    param_str = ", ".join(f"{k}={v}" for k, v in service_data.items())
                    message += f" with parameters: {param_str}"
            
            if self.speak_function:
                active_personality = get_active_personality()
                await self.speak_function(message, personality_name=active_personality)
            if self.display:
                self.display.add_conversation(message, speaker='assistant')
            if self.update_history:
                self.update_history(message, "")
                
            # Get updated state after the action
            updated_state = self.controller.get_entity_state(entity_id)
            
            return {
                "success": True,
                "entity_id": entity_id,
                "service": service,
                "service_data": service_data,
                "message": message,
                "previous_state": current_state,
                "current_state": updated_state
            }
        else:
            message = f"Failed to control {entity_id} with service {service}"
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
