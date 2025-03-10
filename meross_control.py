#!/usr/bin/env python3
"""
meross_control.py - Provides a MerossController class for device initialization and control.
The controller is responsible for initializing the connection, discovering devices,
and offering action functions for turning lights on or off.
"""

import os
import asyncio
from logger_config import get_logger
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

# Get a logger for this module
logger = get_logger(__name__)

class MerossController:
    _instance = None
    
    def __init__(self, http_api_client, manager, devices):
        self.http_api_client = http_api_client
        self.manager = manager
        self.devices = devices
        # Store the instance for singleton access
        MerossController._instance = self

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the controller."""
        return cls._instance

    @classmethod
    async def init(cls):
        email = os.getenv("MEROSS_EMAIL")
        password = os.getenv("MEROSS_PASSWORD")
        if not email or not password:
            raise ValueError("MEROSS_EMAIL and MEROSS_PASSWORD must be set in the environment.")
        
        http_api_client = await MerossHttpClient.async_from_user_password(
            api_base_url='https://iotx-us.meross.com',
            email=email, 
            password=password
        )
        manager = MerossManager(http_client=http_api_client)
        await manager.async_init()
        await manager.async_device_discovery()
        devices = manager.find_devices()
        if not devices:
            logger.warning("No devices found...")
        else:
            logger.info("Discovered devices: %s", [dev.name for dev in devices])
        return cls(http_api_client, manager, devices)

    async def turn_on_light(self):
        if not self.devices:
            logger.warning("No devices available to turn on.")
            return
        for dev in self.devices:
            await dev.async_update()
            logger.info("Turning on %s...", dev.name)
            await dev.async_turn_on(channel=0)

    async def turn_off_light(self):
        if not self.devices:
            logger.warning("No devices available to turn off.")
            return
        for dev in self.devices:
            await dev.async_update()
            logger.info("Turning off %s...", dev.name)
            await dev.async_turn_off(channel=0)

    async def close(self):
        """Properly close the manager and client connections."""
        logger.debug("Closing Meross manager and connections...")
        try:
            if self.manager:
                await self.manager.async_close()
                logger.debug("Meross manager closed successfully")
            
            if self.http_api_client:
                await self.http_api_client.async_logout()
                logger.debug("Meross HTTP client logged out successfully")
            
            # Clear the singleton instance
            MerossController._instance = None
        except Exception as e:
            logger.error(f"Error closing Meross connections: {e}")
        
    # Keep the old method name for backward compatibility
    async def shutdown(self):
        """Legacy method, use close() instead."""
        logger.warning("shutdown() is deprecated, use close() instead")
        await self.close()
