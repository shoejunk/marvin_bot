#!/usr/bin/env python3
"""
main.py - Main entry point for the voice assistant.
Coordinates the voice input processing, AI response generation, and action execution.
"""

import os
os.environ['PATH'] += os.pathsep + os.path.join(os.path.dirname(__file__), 'bin')
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import json
import time
from speech import transcribe_speech_to_text
from tts import speak_text
from llm import get_ai_response
from conversation_history import update_history
from spotify import SpotifyClient
from file_operations import FileOperations
from display import Display
from browser_use.browser.browser import Browser, BrowserConfig
from dotenv import load_dotenv
from logger_config import get_logger, shutdown_logging
from settings_manager import load_settings, update_setting, get_active_personality
from voice_processor import VoiceProcessor
from action_processor import ActionProcessor
from assistant_manager import AssistantManager
from personalities import get_personality, list_personalities
from waiting_sound import play_waiting_sound_once
from context_store import update_home_assistant_devices, update_home_assistant_services, update_home_assistant_climate_devices

# Load environment variables from .env file
load_dotenv()

# Configure browser
browser = Browser(
    config=BrowserConfig(
        chrome_instance_path=os.getenv('CHROME_PATH', '/Program Files (x86)/Google/Chrome/Application/chrome.exe'),
    )
)

# Get a logger for this module using the new configuration
logger = get_logger(__name__)
logger.debug("Main module initialized")

# Initialize display
display = Display()

async def async_main():
    """Main asynchronous function that runs the assistant."""
    # Get active personality
    active_personality = get_active_personality()
    personality = get_personality(active_personality)
    logger.debug(f"Active personality: {personality.name}")
    logger.debug(f"System prompt: {personality.system_prompt}")
    
    # Initialize components
    spotify_client = SpotifyClient()
    file_ops = FileOperations()
    logger.debug("File operations initialized with artifacts directory: %s", file_ops.artifacts_dir)
    
    # Load settings
    settings = load_settings()
    wake_word_required = settings.get("wake_word_required", True)
    
    # Initialize processors
    voice_processor = VoiceProcessor(
        transcribe_function=lambda: asyncio.to_thread(transcribe_speech_to_text),
        display=display,
        update_history_function=update_history
    )
    voice_processor.set_wake_word_required(wake_word_required)
    
    action_processor = ActionProcessor(
        spotify_client=spotify_client,
        file_ops=file_ops,
        display=display,
        speak_function=speak_text,
        update_history_function=update_history,
        browser=browser,
        voice_processor=voice_processor
    )
    action_processor.set_wake_word_required(wake_word_required)
    
    # Initialize Home Assistant handler if configured
    if action_processor.home_assistant:
        action_processor.home_assistant.set_dependencies(
            speak_function=speak_text,
            display=display,
            update_history=update_history
        )
        
        # Load Home Assistant devices at startup and add to persistent context store
        try:
            # Get all climate devices
            climate_devices = action_processor.home_assistant.controller.get_climate_devices()
            if climate_devices:
                # Update climate devices in the persistent context store
                update_home_assistant_climate_devices(climate_devices)
                logger.info(f"Loaded {len(climate_devices)} climate devices from Home Assistant")
            
            # Get all smart devices and their available services
            smart_devices = action_processor.home_assistant.controller.get_devices()
            if smart_devices:
                # Update devices in the persistent context store
                update_home_assistant_devices(smart_devices)
                logger.info(f"Loaded {len(smart_devices)} smart devices from Home Assistant")
                
                # Get available services for each domain
                try:
                    services = action_processor.home_assistant.controller.get_services()
                    if services:
                        # Update services in the persistent context store
                        update_home_assistant_services(services)
                except Exception as e:
                    logger.error(f"Error getting Home Assistant services: {e}")
                
        except Exception as e:
            logger.error(f"Error loading Home Assistant devices: {e}")
            
        logger.info("Home Assistant integration initialized")
    
    try:
        # Initialize with the active personality's name
        await speak_text(f"{personality.name} online", personality_name=active_personality)
        logger.info(f"Wake word requirement is currently {'ON' if wake_word_required else 'OFF'}")
        logger.info(f"Active personality is {personality.name}")
        
        while True:
            # Process voice input
            command, wake_word_detected = await voice_processor.process_voice_input()
            
            if not command:
                continue
                
            # Get AI response using a thread since it may block
            logger.debug(f"Sending to LLM: '{command}'")
            active_personality = get_active_personality()  # Check for updates
            reply = await asyncio.to_thread(get_ai_response, command, active_personality)
            
            logger.info(f"{get_personality(active_personality).name}'s original reply: {reply}")
            
            try:
                # Parse the JSON response
                response_data = json.loads(reply)
                
                # Extract actions to perform
                actions = response_data.get("actions", [])
                
                # Debug logging for actions
                logger.debug(f"Actions received: {actions}")
                
                # Check for personality change action first before processing other actions
                personality_changed = False
                
                # Process actions if any exist
                if actions:
                    # First check for personality change
                    for i in range(len(actions)):
                        action = actions[i]
                        logger.debug(f"Checking action: {action}")
                        
                        if action.get("name") == "change_personality":
                            parameters = action.get("parameters", [])
                            logger.debug(f"Found change_personality action with parameters: {parameters}")
                            
                            if parameters and len(parameters) > 0:
                                new_personality = parameters[0].lower()
                                logger.debug(f"Attempting to change to personality: {new_personality}")
                                
                                # Only change if it's different from current
                                if new_personality != active_personality:
                                    logger.info(f"Changing personality from {active_personality} to {new_personality}")

                                    # Add conversation to display and history
                                    text_to_speak = voice_processor.add_to_conversation(command, reply)

                                    # Speak the response with the old personality
                                    if text_to_speak:
                                        logger.info(f"{personality.name} says: {text_to_speak}")
                                        await speak_text(text_to_speak, personality_name=active_personality)

                                    # Update the active personality
                                    if update_setting("active_personality", new_personality):

                                        # Get the new personality
                                        active_personality = new_personality
                                        personality = get_personality(active_personality)
                                        logger.info(f"Changed personality to {personality.name}")
                                        
                                        # Remove this action so it's not processed again
                                        actions.pop(i)
                                        
                                        # Flag that we've changed personality
                                        personality_changed = True
                                        
                                        # Process remaining actions
                                        if actions:
                                            await action_processor.process_actions(
                                                actions, 
                                                update_setting_function=update_setting
                                            )
                                        
                                        # Break out of the loop to avoid processing the same command twice
                                        break
                
                # Only process if we haven't changed personality
                if not personality_changed:
                    # Add conversation to display and history
                    text_to_speak = voice_processor.add_to_conversation(command, reply)
                    
                    # Speak the response with the active personality
                    if text_to_speak:
                        logger.info(f"{get_personality(active_personality).name} says: {text_to_speak}")
                        await speak_text(text_to_speak, personality_name=active_personality)
                    
                    # Process all actions
                    result = await action_processor.process_actions(
                        actions, 
                        update_setting_function=update_setting
                    )
                    
                play_waiting_sound_once()

            except json.JSONDecodeError:
                logger.error("Failed to parse response as JSON")
                display.add_conversation("Error: Failed to parse response as JSON", speaker='assistant')
                await speak_text("I encountered an error processing your request.", personality_name=active_personality)
            
            except Exception as e:
                logger.error(f"Error processing response: {e}")
                display.add_conversation(f"Error: {str(e)}", speaker='assistant')
                await speak_text("I encountered an error processing your request.", personality_name=active_personality)
                
    except Exception as e:
        logger.error(f"Error in async_main: {e}")
        active_personality = get_active_personality()
        await speak_text("I encountered a critical error and need to shut down.", personality_name=active_personality)
        raise

# Helper function to shut down Meross controller
async def shutdown_meross():
    """Safely shut down the Meross controller."""
    try:
        # Import here to avoid circular imports
        from meross_control import MerossController
        
        # Get the singleton instance and close it
        controller = MerossController.get_instance()
        if controller:
            logger.debug("Shutting down Meross controller...")
            await controller.close()
            logger.debug("Meross controller shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down Meross controller: {e}")

def main():
    """Main entry point for the application."""
    # Initialize the assistant manager
    assistant_manager = AssistantManager(
        async_main_function=async_main,
        display=display,
        shutdown_meross_function=shutdown_meross,
        shutdown_logging_function=shutdown_logging
    )
    
    # Run the assistant
    assistant_manager.run()

if __name__ == "__main__":
    main()