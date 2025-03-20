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
from collections import deque
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
from personalities import get_personality, get_all_personalities
from waiting_sound import play_waiting_sound_once
from context_store import update_home_assistant_devices, update_home_assistant_services, update_home_assistant_climate_devices
from actions import mute_reply_actions

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

speech_queue = []

async def add_to_speech_queue(text, personality_name=None):
    speech_queue.append((text, personality_name))

async def process_speech_queue():
    while speech_queue:
        text, personality_name = speech_queue.pop(0)
        await speak_text(text, personality_name=personality_name)

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
        voice_processor=voice_processor,
        add_to_speech_queue_function=add_to_speech_queue
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
        await add_to_speech_queue(f"{personality.name} online", personality_name=active_personality)
        logger.info(f"Wake word requirement is currently {'ON' if wake_word_required else 'OFF'}")
        logger.info(f"Active personality is {personality.name}")
        
        while True:
            logger.info(f"Processing speech queue")
            await process_speech_queue()

            # Process voice input
            command, wake_word_detected = await voice_processor.process_voice_input()

            await process_speech_queue()

            if not command:
                continue

            display.add_conversation(command, speaker='user')

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

                for i in range(len(actions)):
                    action = actions[i]
                    action_name = action.get("name")

                    friendly_action_name = action_name.replace("_", " ")
                    display.add_conversation(friendly_action_name, speaker='action')

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
                                        await add_to_speech_queue(text_to_speak, personality_name=active_personality)
                                    
                                    # Change the personality
                                    update_setting("active_personality", new_personality)
                                    
                                    # Get the new personality
                                    active_personality = get_active_personality()
                                    personality = get_personality(active_personality)
                                    
                                    # Announce the change
                                    change_message = f"I'm now {personality.name}."
                                    logger.info(change_message)
                                    await add_to_speech_queue(change_message, personality_name=active_personality)
                                    
                                    # Skip processing other actions
                                    break
                    
                    # Process other actions
                    ha_action_detected = False
                    ha_action_results = []
                    
                    for i in range(len(actions)):
                        action = actions[i]
                        action_name = action.get("name")

                        friendly_action_name = action_name.replace("_", " ")

                        # Check if this is a Home Assistant action
                        if action_name in ['get_weather', 'get_thermostat', 'set_thermostat', 'control_entity', 
                                          'list_climate_devices', 'get_smart_devices']:
                            ha_action_detected = True
                            parameters = action.get("parameters", [])

                            # Let the user know they are looking it up
                            # Strip underscores from action name
                            await add_to_speech_queue(f"I'm doing a {friendly_action_name} query for you.", personality_name=active_personality)
                            await process_speech_queue()
                            
                            # Process the action
                            result = await action_processor.process_actions([action], update_setting)
                            if result:
                                ha_action_results.append(result)
                    
                    # If Home Assistant actions were detected, get a follow-up response from the LLM
                    if ha_action_detected and ha_action_results:
                        logger.info("Home Assistant action detected, getting follow-up response from LLM")
                        
                        # Get context for LLM including Home Assistant query results
                        from context_store import get_context_for_llm
                        ha_context = get_context_for_llm()
                        
                        # Get a follow-up response from the LLM
                        follow_up_reply = await asyncio.to_thread(
                            get_ai_response, 
                            f"Please provide a natural language response to the user's query: '{command}' " +
                            "based on the Home Assistant query results. Do not include any actions in your response.",
                            active_personality,
                            additional_context=ha_context
                        )
                        
                        try:
                            # Parse the JSON response
                            follow_up_data = json.loads(follow_up_reply)

                            logger.info(f"Follow-up response from LLM: {follow_up_data}")

                            # Extract the text response
                            text_to_speak = follow_up_data.get("response", "")
                            
                            # Add conversation to display and history
                            voice_processor.add_to_conversation(command, follow_up_reply)
                            
                            # Speak the response
                            if text_to_speak:
                                logger.info(f"{personality.name} says: {text_to_speak}")
                                await add_to_speech_queue(text_to_speak, personality_name=active_personality)
                            else:
                                logger.warning("No text to speak found in follow-up response")
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse follow-up response as JSON: {follow_up_reply}")
                            # Use the follow-up reply directly if it's not valid JSON
                            voice_processor.add_to_conversation(command, follow_up_reply)
                            await add_to_speech_queue(follow_up_reply, personality_name=active_personality)
                        except Exception as e:
                            logger.error(f"Error processing follow-up response: {e}")
                            await add_to_speech_queue("I encountered an error processing the response.", personality_name=active_personality)
                    else:
                        # Process all actions normally
                        await action_processor.process_actions(actions, update_setting)

                        # Check if all actions are muted, in which case don't add the reply to the conversation
                        all_actions_muted = True
                        for action in actions:
                            logger.info(f"Action: {action.get('name')}")
                            if action.get("name") not in mute_reply_actions:
                                logger.info(f"Action not in mute list: {action.get('name')}")
                                all_actions_muted = False

                        if all_actions_muted:
                            reply = ""
                        
                        # Add conversation to display and history
                        text_to_speak = voice_processor.add_to_conversation(command, reply)

                        # Speak the response
                        if text_to_speak and not all_actions_muted:
                            logger.info(f"{personality.name} says: {text_to_speak}")
                            await add_to_speech_queue(text_to_speak, personality_name=active_personality)
                else:
                    # No actions, just speak the response
                    text_to_speak = voice_processor.add_to_conversation(command, reply)
                    
                    if text_to_speak:
                        logger.info(f"{personality.name} says: {text_to_speak}")
                        await add_to_speech_queue(text_to_speak, personality_name=active_personality)
                
                play_waiting_sound_once()

            except json.JSONDecodeError:
                logger.error("Failed to parse response as JSON")
                display.add_conversation("Error: Failed to parse response as JSON", speaker='assistant')
                await add_to_speech_queue("I encountered an error processing your request.", personality_name=active_personality)
            
            except Exception as e:
                logger.error(f"Error processing response: {e}")
                display.add_conversation(f"Error: {str(e)}", speaker='assistant')
                await add_to_speech_queue("I encountered an error processing your request.", personality_name=active_personality)
                
    except Exception as e:
        logger.error(f"Error in async_main: {e}")
        active_personality = get_active_personality()
        await add_to_speech_queue("I encountered a critical error and need to shut down.", personality_name=active_personality)
        raise

def main():
    """Main entry point for the application."""
    # Initialize the assistant manager
    assistant_manager = AssistantManager(
        async_main_function=async_main,
        display=display,
        shutdown_logging_function=shutdown_logging
    )
    
    # Run the assistant
    assistant_manager.run()

if __name__ == "__main__":
    main()