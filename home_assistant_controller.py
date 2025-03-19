#!/usr/bin/env python3
"""
home_assistant_controller.py - Controller for Home Assistant API.
This module handles communication with the Home Assistant API.
"""

import os
import json
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

# Load environment variables
load_dotenv()

class HomeAssistantController:
    """Controller for Home Assistant API."""
    
    def __init__(self, url: str, token: str):
        """Initialize the controller.
        
        Args:
            url: Home Assistant URL
            token: Home Assistant access token
        """
        self.url = url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        logger.debug(f"Initialized Home Assistant controller with URL: {url}")
    
    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states.
        
        Returns:
            List of entity states
        """
        endpoint = f"{self.url}/api/states"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(endpoint, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get states: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error getting states: {e}")
                return []
    
    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get state of a specific entity.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity state or None if not found
        """
        endpoint = f"{self.url}/api/states/{entity_id}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(endpoint, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get state for {entity_id}: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error getting state for {entity_id}: {e}")
                return None
    
    async def call_service(self, domain: str, service: str, service_data: Dict[str, Any] = None) -> bool:
        """Call a Home Assistant service.
        
        Args:
            domain: Service domain
            service: Service name
            service_data: Service data
            
        Returns:
            True if successful, False otherwise
        """
        if service_data is None:
            service_data = {}
            
        endpoint = f"{self.url}/api/services/{domain}/{service}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(endpoint, headers=self.headers, json=service_data) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Failed to call service {domain}.{service}: {response.status}")
                        return False
            except Exception as e:
                logger.error(f"Error calling service {domain}.{service}: {e}")
                return False
    
    async def get_config(self) -> Optional[Dict[str, Any]]:
        """Get Home Assistant configuration.
        
        Returns:
            Configuration or None if failed
        """
        endpoint = f"{self.url}/api/config"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(endpoint, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get config: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error getting config: {e}")
                return None
    
    async def get_services(self) -> Optional[Dict[str, Any]]:
        """Get available services.
        
        Returns:
            Services or None if failed
        """
        endpoint = f"{self.url}/api/services"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(endpoint, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get services: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error getting services: {e}")
                return None
    
    async def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all entities of a specific domain.
        
        Args:
            domain: Entity domain
            
        Returns:
            List of entities
        """
        states = await self.get_states()
        return [state for state in states if state.get("entity_id", "").startswith(f"{domain}.")]
    
    async def get_weather_entities(self) -> List[Dict[str, Any]]:
        """Get all weather entities.
        
        Returns:
            List of weather entities
        """
        return await self.get_entities_by_domain("weather")
    
    async def get_climate_entities(self) -> List[Dict[str, Any]]:
        """Get all climate entities.
        
        Returns:
            List of climate entities
        """
        return await self.get_entities_by_domain("climate")

# Example usage
async def main():
    """Example usage of the HomeAssistantController."""
    # Load environment variables
    load_dotenv()
    
    # Get Home Assistant URL and token from environment variables
    url = os.getenv("HOME_ASSISTANT_URL")
    token = os.getenv("HOME_ASSISTANT_TOKEN")
    
    if not url or not token:
        logger.error("HOME_ASSISTANT_URL or HOME_ASSISTANT_TOKEN not set in .env file")
        return
    
    # Create controller
    controller = HomeAssistantController(url, token)
    
    # Get all states
    states = await controller.get_states()
    logger.info(f"Found {len(states)} entities")
    
    # Get weather entities
    weather_entities = await controller.get_weather_entities()
    logger.info(f"Found {len(weather_entities)} weather entities")
    
    # Get climate entities
    climate_entities = await controller.get_climate_entities()
    logger.info(f"Found {len(climate_entities)} climate entities")

if __name__ == "__main__":
    asyncio.run(main())
