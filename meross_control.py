#!/usr/bin/env python3
"""
meross_control.py - Provides a MerossController class for device initialization and control.
The controller is responsible for initializing the connection, discovering devices,
and offering action functions for turning lights on or off.
"""

import os
import asyncio
import logging
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

class MerossController:
    def __init__(self, http_api_client, manager, devices):
        self.http_api_client = http_api_client
        self.manager = manager
        self.devices = devices

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
            logging.warning("No devices found...")
        else:
            logging.info("Discovered devices: %s", [dev.name for dev in devices])
        return cls(http_api_client, manager, devices)

    async def turn_on_light(self):
        if not self.devices:
            logging.warning("No devices available to turn on.")
            return
        for dev in self.devices:
            await dev.async_update()
            logging.info("Turning on %s...", dev.name)
            await dev.async_turn_on(channel=0)

    async def turn_off_light(self):
        if not self.devices:
            logging.warning("No devices available to turn off.")
            return
        for dev in self.devices:
            await dev.async_update()
            logging.info("Turning off %s...", dev.name)
            await dev.async_turn_off(channel=0)

    async def shutdown(self):
        self.manager.close()
        await self.http_api_client.async_logout()
