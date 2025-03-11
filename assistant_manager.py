#!/usr/bin/env python3
"""
assistant_manager.py - Manages the lifecycle of the Marvin assistant.
Handles starting, stopping, and system tray functionality.
"""

import os
import time
import asyncio
import threading
import logging
import pystray
from PIL import Image

# Import the logger configuration
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

class AssistantManager:
    def __init__(self, async_main_function, display, shutdown_meross_function, shutdown_logging_function):
        """
        Initialize the AssistantManager.
        
        Args:
            async_main_function: The main async function that runs the assistant
            display: Display interface for UI updates
            shutdown_meross_function: Function to shut down Meross controller
            shutdown_logging_function: Function to shut down logging
        """
        self.async_main = async_main_function
        self.display = display
        self.shutdown_meross = shutdown_meross_function
        self.shutdown_logging = shutdown_logging_function
        
        # Global variables to track the running event loop and task
        self.assistant_loop = None
        self.assistant_task = None
        self.tray_icon = None
        
    def start_assistant(self):
        """Start the assistant and create the system tray icon."""
        if self.assistant_loop is not None:
            logger.info('Assistant is already running')
            return
        
        # Start the system tray in a separate thread
        tray_thread = threading.Thread(target=self._create_system_tray, daemon=True)
        tray_thread.start()
        
        logger.info('Starting assistant...')
        self.assistant_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.assistant_loop)
        self.assistant_task = self.assistant_loop.create_task(self.async_main())
        self.assistant_loop.run_until_complete(self.assistant_task)
        
    async def stop_assistant(self):
        """Stop the assistant and clean up resources."""
        logger.info("Stopping assistant...")
        
        try:
            # Cancel the assistant task if it's running
            if self.assistant_task and not self.assistant_task.done():
                self.assistant_task.cancel()
                try:
                    # Wait for the task to be cancelled
                    await asyncio.wait_for(self.assistant_task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.error("Timeout waiting for assistant task to cancel")
                except asyncio.CancelledError:
                    logger.debug("Assistant task cancelled successfully")
                except Exception as e:
                    logger.error(f"Error cancelling assistant task: {e}")
            
            # Clean up the event loop
            if self.assistant_loop and self.assistant_loop.is_running():
                # Schedule a callback to stop the loop
                self.assistant_loop.call_soon_threadsafe(self.assistant_loop.stop)
                
                # Wait for the loop to stop (with timeout)
                start_time = time.time()
                while self.assistant_loop.is_running() and time.time() - start_time < 5.0:
                    time.sleep(0.1)
                    
                if self.assistant_loop.is_running():
                    logger.warning("Event loop is still running after timeout")
            
            # Shutdown the Meross controller
            await self.shutdown_meross()
            
            # Properly shut down all loggers
            self.shutdown_logging()
            
            logger.info("Assistant stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping assistant: {e}")
            
    def _create_system_tray(self):
        """Create and run the system tray icon."""
        try:
            image = Image.open('icon.png')
            
            def on_exit(icon):
                logger.info('Exiting Marvin from system tray...')
                asyncio.run(self.stop_assistant())
                icon.stop()
                os._exit(0)  # Force terminate the process
            
            menu = (
                pystray.MenuItem('Start', lambda: self.start_assistant()),
                pystray.MenuItem('Stop', lambda: asyncio.run(self.stop_assistant())),
                pystray.MenuItem('Exit', on_exit)
            )
            
            self.tray_icon = pystray.Icon('Marvin', image, 'Marvin Voice Assistant', menu)
            self.tray_icon.run()
        except Exception as e:
            logger.error(f"Error creating system tray: {e}")
            
    def run(self):
        """Run the assistant in a separate thread and the display in the main thread."""
        # Create a thread for the assistant
        assistant_thread = threading.Thread(target=self.start_assistant, daemon=True)
        assistant_thread.start()
        
        # Run the display GUI in the main thread
        self.display.run()
