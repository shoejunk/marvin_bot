#!/usr/bin/env python3
"""
main.py - Main entry point for the voice assistant.
Processes voice input, obtains AI responses, extracts actions from JSON response,
and triggers actions (e.g., turning lights on/off) via the MerossController and file operations.
"""

import os
os.environ['PATH'] += os.pathsep + os.path.join(os.path.dirname(__file__), 'bin')
import re
import asyncio
import sys
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess
from speech import transcribe_speech_to_text
from tts import speak_text
from llm import get_ai_response, system_prompt
from waiting_sound import play_waiting_sound
from meross_control import MerossController
from actions import action_strings  # Import shared valid actions list
from dictate import handle_dictate  # Import dictate function from new module
from conversation_history import update_history
from spotify import SpotifyClient
from file_operations import FileOperations  # Import the new FileOperations class
from datetime import timedelta
import pystray
from PIL import Image
import threading
import json
from display import Display
from browser_use.agent.views import ActionResult
from browser_use import Agent  # Import the Agent class from browser_use
from langchain_openai import ChatOpenAI  # Import ChatOpenAI
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from dotenv import load_dotenv
# Import the new logger configuration
from logger_config import get_logger, shutdown_logging
# Import settings manager
from settings_manager import load_settings, update_setting

# Load environment variables from .env file
load_dotenv()

browser = Browser(
	config=BrowserConfig(
		chrome_instance_path=os.getenv('CHROME_PATH', '/Program Files (x86)/Google/Chrome/Application/chrome.exe'),
	)
)

# Get a logger for this module using the new configuration
logger = get_logger(__name__)
logger.debug("Main module initialized")

display = Display()

# Add global timer control variable
if 'timer_counter' not in globals():
    timer_counter = 0

# Load settings from settings.json
settings = load_settings()
wake_word_required = settings.get("wake_word_required", True)
logger.info(f"Loaded wake_word_required setting: {wake_word_required}")

def get_time():
    import datetime
    now = datetime.datetime.now()
    return now.strftime('%I:%M %p').lstrip('0')

async def async_main():
    global wake_word_required
    
    logger.debug("System prompt: %s", system_prompt)
    logger.debug("Initializing Meross Controller...")
    meross_controller = await MerossController.init()
    spotify_client = SpotifyClient()
    
    # Initialize the file operations manager
    file_ops = FileOperations()
    logger.debug("File operations initialized with artifacts directory: %s", file_ops.artifacts_dir)
    
    try:
        await speak_text("Marvin online")
        logger.info(f"Wake word requirement is currently {'ON' if wake_word_required else 'OFF'}")
        
        while True:
            # Get user input from speech transcription.
            try:
                user_input = await asyncio.to_thread(transcribe_speech_to_text)
            except TimeoutError:
                logger.error("Error: Connection timed out while transcribing speech.")
                continue
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                continue

            if not user_input:
                continue

            logger.info(f"Wake word requirement is currently {'ON' if wake_word_required else 'OFF'}")

            # Process commands only if a valid wake word is detected or wake word is not required
            wake_words = ["marvin", "hey marvin", "ok marvin", "okay marvin", "hi marvin"]
            wake_words += ["martin", "hey martin", "ok martin", "okay martin", "hi martin"]
            wake_words += ["computer", "hey computer", "ok computer", "okay computer", "hi computer"]
            wake_words += ["PC", "hey PC", "ok PC", "okay PC", "hi PC"]
            user_input_lower = user_input.lower()
            matched_wake_word = None
            
            # Check for wake word if required
            if wake_word_required:
                for wake_word in wake_words:
                    if user_input_lower.startswith(wake_word):
                        matched_wake_word = wake_word
                        break

                if not matched_wake_word:
                    logger.info("Waiting for wake word...")
                    continue

                # Remove the detected wake word from the beginning of the input.
                command = user_input[len(matched_wake_word):].strip()
                logger.debug(f"Wake word detected: '{matched_wake_word}', command: '{command}'")
            else:
                # Wake word not required, process the entire input
                command = user_input
                logger.info(f"Wake word OFF - Processing input without wake word: '{command}'")

            # Get AI response using a thread since it may block.
            logger.debug(f"Sending to LLM: '{command}'")
            reply = await asyncio.to_thread(get_ai_response, command)

            logger.info(f"Marvin's original reply: {reply}")

            try:
                # Parse the JSON response
                response_data = json.loads(reply)
                
                # Extract the text response to speak
                text_to_speak = response_data.get("response", "")
                
                # Extract actions to perform
                actions = response_data.get("actions", [])
                
                # Update conversation history with the current turn
                display.add_conversation(user_input, speaker='user')
                display.add_conversation(text_to_speak, speaker='marvin')
                
                # Update the conversation history
                update_history(user_input, reply)

                if text_to_speak:
                    logger.info(f"Marvin says: {text_to_speak}")
                    await speak_text(text_to_speak)

                # Process each action in the actions array
                for action_item in actions:
                    action_name = action_item.get("name", "").lower()
                    params = action_item.get("parameters", [])
                    
                    # Log the action
                    if params:
                        logger.info(f"Detected action: {action_name} with params: {params}")
                        display.add_conversation(f"Action: {action_name} with params: {params}")
                        update_history(f"Action: {action_name} with params: {params}", "")
                    else:
                        logger.info(f"Detected action: {action_name}")
                        display.add_conversation(f"Action: {action_name}")
                        update_history(f"Action: {action_name}", "")
                    
                    # Handle wake word toggle actions
                    if action_name == "wake_word_off":
                        wake_word_required = False
                        # Save the setting
                        update_setting("wake_word_required", False)
                        logger.info("Wake word requirement turned OFF and saved to settings")
                        display.add_conversation("Wake word requirement turned OFF")
                        update_history("Wake word requirement turned OFF", "")
                    elif action_name == "wake_word_on":
                        wake_word_required = True
                        # Save the setting
                        update_setting("wake_word_required", True)
                        logger.info("Wake word requirement turned ON and saved to settings")
                        display.add_conversation("Wake word requirement turned ON")
                        update_history("Wake word requirement turned ON", "")
                    # Handle existing actions
                    elif action_name == "turn_on_light":
                        await meross_controller.turn_on_light()
                    elif action_name == "turn_off_light":
                        await meross_controller.turn_off_light()
                    elif action_name == "play_song":
                        song_name = params[0] if params else ''
                        if song_name:
                            spotify_client.play_track(song_name)
                    elif action_name == "play_music":
                        song_or_artist = params[0] if params else ''
                        if song_or_artist:
                            spotify_client.play_music(song_or_artist)
                    elif action_name == "play_playlist":
                        playlist_name = params[0] if params else ''
                        if playlist_name:
                            spotify_client.play_playlist(playlist_name)
                    elif action_name == "pause_music":
                        spotify_client.pause_music()
                    elif action_name == "unpause_music" or action_name == "resume_music":
                        spotify_client.resume_music()
                    elif action_name == "stop_music":
                        spotify_client.stop_music()
                    elif action_name == "next_track":
                        spotify_client.next_track()
                    elif action_name == "previous_track":
                        spotify_client.previous_track()
                    elif action_name == "volume_up":
                        increment = int(params[0]) if params and params[0].isdigit() else 10
                        spotify_client.volume_up(increment)
                    elif action_name == "volume_down":
                        decrement = int(params[0]) if params and params[0].isdigit() else 10
                        spotify_client.volume_down(decrement)
                    elif action_name == "adjust_volume":
                        level = params[0] if params else '50'
                        spotify_client.adjust_volume(level)
                    elif action_name == "reboot":
                        logger.info("Rebooting Marvin...")
                        bat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "run_marvin.bat"))
                        logger.info(f"Running batch file: {bat_path}")
                        subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                        os._exit(0)
                    elif action_name == 'set_timer' or action_name == 'start_timer':
                        duration = params[0] if params else ''
                        if duration:
                            # Replace underscores with spaces if present
                            duration = duration.replace('_', ' ')
                            logger.info(f"Setting timer with cleaned duration: '{duration}'")
                            asyncio.create_task(set_timer(duration))
                    elif action_name == 'stop_timer':
                        await stop_timer()
                    elif action_name == 'shut_down':
                        await speak_text('Shutting down Marvin')
                        logger.info('Shutting down Marvin...')
                        # Ensure Meross controller is properly shut down
                        await meross_controller.shutdown()
                        stop_assistant()
                        os._exit(0)
                        
                    # File operation actions
                    elif action_name == 'read_file':
                        filename = params[0] if params else None
                        if filename:
                            content = file_ops.read_file(filename)
                            if content is not None:
                                # Add file content to conversation history but don't display it
                                update_history(f"Content of file {filename}:\n{content}", "")
                                # Inform the user that the file has been read
                                await speak_text(f"I've read the file {filename} and added its content to my context.")
                            else:
                                await speak_text(f"Could not read file {filename}")
                        else:
                            await speak_text("No filename specified for reading")
                    
                    elif action_name == 'write_file':
                        if len(params) >= 2:
                            filename = params[0]
                            content = params[1]
                            overwrite = True if len(params) <= 2 or params[2].lower() == 'true' else False
                            success = file_ops.write_file(filename, content, overwrite)
                            if success:
                                await speak_text(f"Successfully wrote to file {filename}")
                            else:
                                await speak_text(f"Failed to write to file {filename}")
                        else:
                            await speak_text("Insufficient parameters for writing a file")
                            
                    elif action_name == 'list_files':
                        subdirectory = params[0] if params else ""
                        files = file_ops.list_files(subdirectory)
                        if files:
                            files_str = ", ".join(files)
                            await speak_text(f"Files in {subdirectory or 'artifacts directory'}: {files_str}")
                            update_history(f"Files in {subdirectory or 'artifacts directory'}: {files_str}", "")
                        else:
                            await speak_text(f"No files found in {subdirectory or 'artifacts directory'}")
                            update_history(f"No files found in {subdirectory or 'artifacts directory'}", "")
                            
                    elif action_name == 'delete_file':
                        filename = params[0] if params else None
                        if filename:
                            success = file_ops.delete_file(filename)
                            if success:
                                await speak_text(f"Successfully deleted file {filename}")
                            else:
                                await speak_text(f"Failed to delete file {filename}")
                        else:
                            await speak_text("No filename specified for deletion")
                            
                    elif action_name == 'append_to_file':
                        if len(params) >= 2:
                            filename = params[0]
                            content = params[1]
                            create_if_missing = True if len(params) <= 2 or params[2].lower() == 'true' else False
                            success = file_ops.append_to_file(filename, content, create_if_missing)
                            if success:
                                await speak_text(f"Successfully appended to file {filename}")
                            else:
                                await speak_text(f"Failed to append to file {filename}")
                        else:
                            await speak_text("Insufficient parameters for appending to a file")
                            
                    elif action_name == 'edit_file':
                        if len(params) >= 3:
                            filename = params[0]
                            find_text = params[1]
                            replace_text = params[2]
                            success = file_ops.edit_file(filename, find_text, replace_text)
                            if success:
                                await speak_text(f"Successfully edited file {filename}")
                            else:
                                await speak_text(f"Failed to edit file {filename}")
                        else:
                            await speak_text("Insufficient parameters for editing a file")
                            
                    elif action_name == 'create_directory':
                        directory_name = params[0] if params else None
                        if directory_name:
                            success = file_ops.create_directory(directory_name)
                            if success:
                                await speak_text(f"Successfully created directory {directory_name}")
                            else:
                                await speak_text(f"Failed to create directory {directory_name}")
                        else:
                            await speak_text("No directory name specified for creation")
                            
                    elif action_name == 'copy_file':
                        if len(params) >= 2:
                            source = params[0]
                            destination = params[1]
                            success = file_ops.copy_file(source, destination)
                            if success:
                                await speak_text(f"Successfully copied file from {source} to {destination}")
                            else:
                                await speak_text(f"Failed to copy file from {source} to {destination}")
                        else:
                            await speak_text("Insufficient parameters for copying a file")
                            
                    elif action_name == 'move_file':
                        if len(params) >= 2:
                            source = params[0]
                            destination = params[1]
                            success = file_ops.move_file(source, destination)
                            if success:
                                await speak_text(f"Successfully moved file from {source} to {destination}")
                            else:
                                await speak_text(f"Failed to move file from {source} to {destination}")
                        else:
                            await speak_text("Insufficient parameters for moving a file")
                            
                    elif action_name == 'search_files':
                        if len(params) >= 1:
                            search_text = params[0]
                            subdirectory = params[1] if len(params) > 1 else ""
                            results = file_ops.search_files(search_text, subdirectory)
                            if results:
                                results_str = ", ".join(results)
                                await speak_text(f"Found {len(results)} files containing '{search_text}': {results_str}")
                                update_history(f"Files containing '{search_text}': {results_str}", "")
                            else:
                                await speak_text(f"No files found containing '{search_text}'")
                                update_history(f"No files found containing '{search_text}'", "")
                        else:
                            await speak_text("No search text specified")
                            
                    elif action_name == 'dictate':
                        target_file = params[0] if params else "dictation.txt"
                        await handle_dictate(target_file, file_ops)
                        
                    elif action_name == 'write_code':
                        if len(params) >= 2:
                            filename = params[0]
                            code_content = params[1]
                            success = file_ops.write_file(filename, code_content, True)
                            if success:
                                await speak_text(f"Successfully wrote code to file {filename}")
                            else:
                                await speak_text(f"Failed to write code to file {filename}")
                        else:
                            await speak_text("Insufficient parameters for writing code")
                    
                    # Browser use action
                    elif action_name == 'browse_internet':
                        query = params[0] if params else None
                        if query:
                            display.add_conversation(f"Browsing the internet for: {query}", speaker='marvin')
                            update_history(f"Browsing the internet for: {query}", "")
                            try:
                                # Set up a custom log handler to capture the browser_use agent's output
                                class BrowserUseLogHandler(logging.Handler):
                                    def __init__(self):
                                        super().__init__()
                                        self.result = None
                                    
                                    def emit(self, record):
                                        if record.name == 'browser_use.agent.service' and 'Result:' in record.getMessage():
                                            # Extract the result from the log message
                                            result_msg = record.getMessage()
                                            if '\U0001f4c4 Result:' in result_msg:
                                                self.result = result_msg.split('\U0001f4c4 Result:')[1].strip()
                                            elif 'Result:' in result_msg:
                                                self.result = result_msg.split('Result:')[1].strip()
                                
                                # Add the custom log handler
                                browser_log_handler = BrowserUseLogHandler()
                                browser_log_handler.setLevel(logging.INFO)
                                logging.getLogger('browser_use').addHandler(browser_log_handler)
                                
                                # Create and run the browser agent
                                await browser.close()
                                agent = Agent(
                                    task=query,
                                    llm=ChatOpenAI(model="gpt-4o"),
                                    browser=browser,
                                )
                                await agent.run()
                                
                                # Remove the custom log handler
                                logging.getLogger('browser_use').removeHandler(browser_log_handler)
                                
                                # Check if we captured a result
                                if browser_log_handler.result:
                                    result_text = browser_log_handler.result
                                    
                                    # Send the result to the LLM for summarization
                                    summarization_prompt = f"Below are the results from a web search. Please provide a concise summary of these results, while preserving the key information:\n\n{result_text}"
                                    summary_response = get_ai_response(summarization_prompt)
                                    
                                    try:
                                        # Parse the JSON response for the summary
                                        summary_data = json.loads(summary_response)
                                        summary_text = summary_data.get("response", "")
                                        
                                        # Display the full results in the UI
                                        display.add_conversation(result_text, speaker='marvin')
                                        
                                        # Update history with full results
                                        update_history(result_text, "")
                                        
                                        # Speak the summarized version
                                        await speak_text(summary_text)
                                    except json.JSONDecodeError:
                                        # Fallback if JSON parsing fails
                                        logger.error("Failed to parse summary response as JSON")
                                        display.add_conversation(result_text, speaker='marvin')
                                        update_history(result_text, "")
                                        await speak_text("I found some information, but couldn't properly format it.")
                                else:
                                    # Default message if we couldn't capture a result
                                    display.add_conversation("Browser search complete, but couldn't extract specific results.", speaker='marvin')
                                    update_history("Browser search complete, but couldn't extract specific results.", "")
                                    await speak_text("Browser search complete, but I couldn't extract specific results.")
                            except Exception as e:
                                error_message = f"Error during browser search: {e}"
                                logger.error(error_message)
                                display.add_conversation(f"❌ {error_message}", speaker='marvin')
                                update_history(f"❌ {error_message}", "")
                                await speak_text("I encountered an error while browsing the internet.")
                        else:
                            await speak_text("No search query specified for browsing the internet.")
                            display.add_conversation("No search query specified for browsing the internet.", speaker='marvin')
                            update_history("No search query specified for browsing the internet.", "")
                            
                    else:
                        logger.warning(f"Unknown action: {action_name}")
                        display.add_conversation(f"Unknown action: {action_name}")
                
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

async def set_timer(duration: str):
    global timer_counter
    try:
        logger.debug(f"Setting timer with duration: '{duration}'")
        
        # First, check if the duration is already in the format "X unit"
        duration_parts = duration.split()
        logger.debug(f"Duration parts: {duration_parts}")
        
        if len(duration_parts) == 2:
            # Format is already "X unit"
            try:
                value = int(duration_parts[0])
                unit_input = duration_parts[1].lower()
                logger.debug(f"Parsed as two parts: value={value}, unit={unit_input}")
            except ValueError as e:
                logger.error(f"Error parsing value: {e}")
                await speak_text('Invalid timer format. The value must be a number.')
                return
        else:
            # Try to parse the duration as a single value
            # Check if it's just a number (assume seconds)
            try:
                value = int(duration)
                unit_input = 'seconds'
                logger.debug(f"Parsed as single number: {value} {unit_input}")
            except ValueError:
                # Try to extract number and unit from a string without spaces
                import re
                match = re.match(r'(\d+)(\w+)', duration)
                if match:
                    try:
                        value = int(match.group(1))
                        unit_abbr = match.group(2).lower()
                        unit_input = unit_abbr
                        logger.debug(f"Parsed with regex: value={value}, unit={unit_input}")
                    except ValueError as e:
                        logger.error(f"Error parsing regex match: {e}")
                        await speak_text('Invalid timer format. Use format like "5 minutes" or "5m".')
                        return
                else:
                    logger.error(f"Could not parse timer format: '{duration}'")
                    await speak_text('Invalid timer format. Use format like "5 minutes" or "5m".')
                    return
        
        # Map any unit format to a standardized format
        unit_map = {
            's': 'second', 'sec': 'second', 'second': 'second', 'seconds': 'second',
            'm': 'minute', 'min': 'minute', 'minute': 'minute', 'minutes': 'minute',
            'h': 'hour', 'hr': 'hour', 'hour': 'hour', 'hours': 'hour'
        }
        
        # Try to map the input unit to a standard unit
        if unit_input in unit_map:
            unit = unit_map[unit_input]
            logger.debug(f"Mapped '{unit_input}' to '{unit}'")
        else:
            logger.error(f"Unknown time unit: '{unit_input}'")
            await speak_text(f'Invalid time unit: "{unit_input}". Use seconds, minutes, or hours.')
            return
            
        # Check if unit is valid (should always be valid after mapping)
        valid_units = ['second', 'minute', 'hour']
        if unit in valid_units:
            # Convert to seconds
            if unit == 'minute':
                seconds_value = value * 60
            elif unit == 'hour':
                seconds_value = value * 3600
            else:  # seconds
                seconds_value = value
                
            # For display purposes, use the original format
            display_unit = unit + ('s' if value != 1 else '')
            
            logger.debug(f"Setting timer for {value} {display_unit} ({seconds_value} seconds)")
            timer_name = f"timer_{timer_counter}"
            timer_counter += 1
            display.add_timer(timer_name, timedelta(seconds=seconds_value))
            await asyncio.sleep(seconds_value)
            display.remove_timer(timer_name)
            await speak_text('Timer complete!')
        else:
            # This should never happen with our mapping
            logger.error(f"Unexpected error: Unit '{unit}' not in valid_units after mapping")
            await speak_text('Invalid time unit. Use seconds, minutes, or hours.')
    except Exception as e:
        logger.error(f'Error setting timer: {e}', exc_info=True)
        await speak_text('Error setting timer.')

async def stop_timer():
    # Stop all active timers by removing each one from the display
    active_timers = list(display.timers.keys())
    for tname in active_timers:
        display.remove_timer(tname)
    logger.info('All timers stopped')

# Global variable to track the running event loop
assistant_loop = None
assistant_task = None

async def stop_assistant():
    """Stop the assistant and clean up resources."""
    global assistant_loop, assistant_task
    
    logger.info("Stopping assistant...")
    
    try:
        # Cancel the assistant task if it's running
        if assistant_task and not assistant_task.done():
            assistant_task.cancel()
            try:
                # Wait for the task to be cancelled
                await asyncio.wait_for(assistant_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for assistant task to cancel")
            except asyncio.CancelledError:
                logger.debug("Assistant task cancelled successfully")
            except Exception as e:
                logger.error(f"Error cancelling assistant task: {e}")
        
        # Clean up the event loop
        if assistant_loop and assistant_loop.is_running():
            # Schedule a callback to stop the loop
            assistant_loop.call_soon_threadsafe(assistant_loop.stop)
            
            # Wait for the loop to stop (with timeout)
            start_time = time.time()
            while assistant_loop.is_running() and time.time() - start_time < 5.0:
                time.sleep(0.1)
                
            if assistant_loop.is_running():
                logger.warning("Event loop is still running after timeout")
        
        # Shutdown the Meross controller
        await shutdown_meross()
        
        # Properly shut down all loggers
        shutdown_logging()
        
        logger.info("Assistant stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping assistant: {e}")

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
    
# Function to create system tray icon
def create_system_tray():
    image = Image.open('icon.png')
    
    def on_exit(icon):
        logger.info('Exiting Marvin from system tray...')
        stop_assistant()
        icon.stop()
        os._exit(0)  # Force terminate the process
    
    menu = (
        pystray.MenuItem('Start', lambda: start_assistant()),
        pystray.MenuItem('Stop', lambda: stop_assistant()),
        pystray.MenuItem('Exit', on_exit)
    )
    icon = pystray.Icon('Marvin', image, 'Marvin Voice Assistant', menu)
    icon.run()

def start_assistant():
    global assistant_loop, assistant_task
    
    if assistant_loop is not None:
        logger.info('Assistant is already running')
        return
    
    # Start the system tray in a separate thread
    tray_thread = threading.Thread(target=create_system_tray, daemon=True)
    tray_thread.start()
    
    logger.info('Starting assistant...')
    assistant_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(assistant_loop)
    assistant_task = assistant_loop.create_task(async_main())
    assistant_loop.run_until_complete(assistant_task)

def main():
    # Create a thread for the assistant
    assistant_thread = threading.Thread(target=start_assistant, daemon=True)
    assistant_thread.start()
    
    # Run the display GUI in the main thread
    display.run()

if __name__ == "__main__":
    main()