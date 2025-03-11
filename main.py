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
from llm import get_ai_response, system_prompt
from waiting_sound import play_waiting_sound
from meross_control import MerossController
from conversation_history import update_history
from spotify import SpotifyClient
from file_operations import FileOperations
from display import Display
from browser_use.browser.browser import Browser, BrowserConfig
from dotenv import load_dotenv
from logger_config import get_logger, shutdown_logging
from settings_manager import load_settings, update_setting
from voice_processor import VoiceProcessor
from action_processor import ActionProcessor
from assistant_manager import AssistantManager

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
    logger.debug("System prompt: %s", system_prompt)
    logger.debug("Initializing Meross Controller...")
    
    # Initialize components
    meross_controller = await MerossController.init()
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
        meross_controller=meross_controller,
        spotify_client=spotify_client,
        file_ops=file_ops,
        display=display,
        speak_function=speak_text,
        update_history_function=update_history,
        browser=browser
    )
    action_processor.set_wake_word_required(wake_word_required)
    
    try:
        await speak_text("Marvin online")
        logger.info(f"Wake word requirement is currently {'ON' if wake_word_required else 'OFF'}")
        
        while True:
            # Process voice input
            command, wake_word_detected = await voice_processor.process_voice_input()
            
            if not command:
                continue
                
            # Get AI response using a thread since it may block
            logger.debug(f"Sending to LLM: '{command}'")
            reply = await asyncio.to_thread(get_ai_response, command)
            
            logger.info(f"Marvin's original reply: {reply}")
            
            try:
                # Add conversation to display and history
                text_to_speak = voice_processor.add_to_conversation(command, reply)
                
                # Speak the response
                if text_to_speak:
                    logger.info(f"Marvin says: {text_to_speak}")
                    await speak_text(text_to_speak)
                
                # Parse the JSON response
                response_data = json.loads(reply)
                
                # Extract actions to perform
                actions = response_data.get("actions", [])
                
                # Process actions
                result = await action_processor.process_actions(
                    actions, 
                    update_setting_function=update_setting
                )
                
                # Check if we need to shut down
                if result == "shutdown":
                    break
                    
            except json.JSONDecodeError:
                logger.error("Failed to parse response as JSON")
                display.add_conversation("Error: Failed to parse response as JSON", speaker='marvin')
                await speak_text("I encountered an error processing your request.")
            
            except Exception as e:
                logger.error(f"Error processing response: {e}")
                display.add_conversation(f"Error: {str(e)}", speaker='marvin')
                await speak_text("I encountered an error processing your request.")
                
    except Exception as e:
        logger.error(f"Error in async_main: {e}")
        await speak_text("I encountered a critical error and need to shut down.")
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