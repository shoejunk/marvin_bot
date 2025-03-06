#!/usr/bin/env python3
"""
main.py - Main entry point for the voice assistant.
Processes voice input, obtains AI responses, strips out <action> tags before speaking,
and triggers actions (e.g., turning lights on/off) via the MerossController and file operations.
"""

import os
os.environ['PATH'] += os.pathsep + os.path.join(os.path.dirname(__file__), 'bin')
import re
import asyncio
import sys
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
import logging
import json
from display import Display

# Adding more detailed logging configuration
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.FileHandler("marvin_debug.log"),
                       logging.StreamHandler()
                   ])

display = Display()

# Add global timer control variable
if 'timer_counter' not in globals():
    timer_counter = 0

def get_time():
    import datetime
    return datetime.datetime.now().strftime('%H:%M')

async def async_main():
    logging.debug("System prompt: %s", system_prompt)
    logging.debug("Initializing Meross Controller...")
    meross_controller = await MerossController.init()
    spotify_client = SpotifyClient()
    
    # Initialize the file operations manager
    file_ops = FileOperations()
    logging.debug("File operations initialized with artifacts directory: %s", file_ops.artifacts_dir)
    
    await speak_text("Marvin online")
    
    while True:
        # Get user input from speech transcription.
        try:
            user_input = await asyncio.to_thread(transcribe_speech_to_text)
        except TimeoutError:
            logging.error("Error: Connection timed out while transcribing speech.")
            continue
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            continue

        if not user_input:
            continue

        # Process commands only if a valid wake word is detected.
        wake_words = ["marvin", "hey marvin", "ok marvin", "okay marvin", "hi marvin"]
        wake_words += ["martin", "hey martin", "ok martin", "okay martin", "hi martin"]
        wake_words += ["computer", "hey computer", "ok computer", "okay computer", "hi computer"]
        wake_words += ["PC", "hey PC", "ok PC", "okay PC", "hi PC"]
        user_input_lower = user_input.lower()
        matched_wake_word = None
        for wake_word in wake_words:
            if user_input_lower.startswith(wake_word):
                matched_wake_word = wake_word
                break

        if not matched_wake_word:
            logging.info("Waiting for wake word...")
            continue

        # Remove the detected wake word from the beginning of the input.
        command = user_input[len(matched_wake_word):].strip()

        # Get AI response using a thread since it may block.
        reply = await asyncio.to_thread(get_ai_response, user_input)

        # Update conversation history with the current turn.
        display.add_conversation(user_input, speaker='user')
        
        # Strip out action tags for display
        display_reply = re.sub(r'<action>.*?</action>', '', reply, flags=re.IGNORECASE)
        display.add_conversation(display_reply, speaker='marvin')

        # Remove any <action> tags from the text before speaking.
        text_to_speak = re.sub(r'<action>.*?</action>', '', reply, flags=re.IGNORECASE)
        text_to_speak = re.sub(r'<[^>]+>', '', text_to_speak).strip()

        # Parse the AI reply for <action> tags to trigger actions.
        action_tags = re.findall(r'<action>(.*?)</action>', reply, flags=re.IGNORECASE)
        for action in action_tags:
            normalized_action = action.lower().replace(" ", "_")
            
            # Extract parameters if they exist (format: action_name:param1,param2)
            params = []
            if ':' in normalized_action:
                action_parts = normalized_action.split(':', 1)
                action_name = action_parts[0]
                params_text = action_parts[1]
                
                # Handle comma-separated parameters
                if ',' in params_text:
                    params = [param.strip() for param in params_text.split(',')]
                else:
                    params = [params_text.strip()]
            else:
                action_name = normalized_action
            
            # Log the action
            if params:
                logging.info(f"Detected action: {action_name} with params: {params}")
                display.add_conversation(f"Action: {action_name} with params: {params}")
            else:
                logging.info(f"Detected action: {action_name}")
                display.add_conversation(f"Action: {action_name}")
            
            # Handle existing actions
            if action_name.startswith("turn_on_light"):
                await meross_controller.turn_on_light()
            elif action_name.startswith("turn_off_light"):
                await meross_controller.turn_off_light()
            elif action_name.startswith("play_song"):
                song_name = params[0] if params else ''
                if song_name:
                    spotify_client.play_track(song_name)
            elif action_name.startswith("play_playlist"):
                playlist_name = params[0] if params else ''
                if playlist_name:
                    spotify_client.play_playlist(playlist_name)
            elif action_name.startswith("pause_music"):
                spotify_client.pause_music()
            elif action_name.startswith("unpause_music"):
                spotify_client.unpause_music()
            elif action_name.startswith("stop_music"):
                spotify_client.stop_music()
            elif action_name.startswith("volume_up"):
                increment = int(params[0]) if params and params[0].isdigit() else 10
                spotify_client.volume_up(increment)
            elif action_name.startswith("volume_down"):
                decrement = int(params[0]) if params and params[0].isdigit() else 10
                spotify_client.volume_down(decrement)
            elif action_name.startswith("reboot"):
                await speak_text("Marvin rebooting")
                logging.info("Rebooting Marvin...")
                bat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "run_marvin.bat"))
                logging.info(f"Running batch file: {bat_path}")
                subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                os._exit(0)
            elif action_name.startswith('set_timer') or action_name.startswith('start_timer'):
                duration = params[0] if params else ''
                if duration:
                    # Replace underscores with spaces if present
                    duration = duration.replace('_', ' ')
                    logging.info(f"Setting timer with cleaned duration: '{duration}'")
                    asyncio.create_task(set_timer(duration))
            elif action_name.startswith('stop_timer'):
                await stop_timer()
            elif action_name.startswith('shut_down'):
                await speak_text('Shutting down Marvin')
                logging.info('Shutting down Marvin...')
                stop_assistant()
                os._exit(0)
                
            # New file operation actions
            elif action_name.startswith('read_file'):
                filename = params[0] if params else None
                if filename:
                    content = file_ops.read_file(filename)
                    if content is not None:
                        # Create a temporary file with the content to be read back
                        temp_file = os.path.join(file_ops.artifacts_dir, "_temp_read.txt")
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            f.write(f"Content of file {filename}:\n{content}")
                        # Read the content out loud with a limit
                        preview = content[:300] + "..." if len(content) > 300 else content
                        await speak_text(f"Content of file {filename}: {preview}")
                    else:
                        await speak_text(f"Could not read file {filename}")
                else:
                    await speak_text("No filename specified for reading")
                    
            elif action_name.startswith('write_file'):
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
                    
            elif action_name.startswith('list_files'):
                subdirectory = params[0] if params else ""
                files = file_ops.list_files(subdirectory)
                if files:
                    file_list = ", ".join(files[:10])
                    if len(files) > 10:
                        file_list += f", and {len(files) - 10} more files"
                    await speak_text(f"Found {len(files)} files: {file_list}")
                else:
                    await speak_text(f"No files found in {'artifacts' if not subdirectory else subdirectory}")
                    
            elif action_name.startswith('delete_file'):
                filename = params[0] if params else None
                if filename:
                    success = file_ops.delete_file(filename)
                    if success:
                        await speak_text(f"Successfully deleted file {filename}")
                    else:
                        await speak_text(f"Failed to delete file {filename}")
                else:
                    await speak_text("No filename specified for deletion")
                    
            elif action_name.startswith('edit_file'):
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
                    
            elif action_name.startswith('append_to_file'):
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
                    
            elif action_name.startswith('create_directory'):
                directory = params[0] if params else None
                if directory:
                    success = file_ops.create_directory(directory)
                    if success:
                        await speak_text(f"Successfully created directory {directory}")
                    else:
                        await speak_text(f"Failed to create directory {directory}")
                else:
                    await speak_text("No directory name specified for creation")
                    
            elif action_name.startswith('move_file'):
                if len(params) >= 2:
                    source = params[0]
                    destination = params[1]
                    success = file_ops.move_file(source, destination)
                    if success:
                        await speak_text(f"Successfully moved file from {source} to {destination}")
                    else:
                        await speak_text(f"Failed to move file")
                else:
                    await speak_text("Insufficient parameters for moving a file")
                    
            elif action_name.startswith('copy_file'):
                if len(params) >= 2:
                    source = params[0]
                    destination = params[1]
                    success = file_ops.copy_file(source, destination)
                    if success:
                        await speak_text(f"Successfully copied file from {source} to {destination}")
                    else:
                        await speak_text(f"Failed to copy file")
                else:
                    await speak_text("Insufficient parameters for copying a file")
                    
            elif action_name.startswith('search_files'):
                if params:
                    search_text = params[0]
                    subdirectory = params[1] if len(params) > 1 else ""
                    matching_files = file_ops.search_files(search_text, subdirectory)
                    if matching_files:
                        file_list = ", ".join(matching_files[:5])
                        if len(matching_files) > 5:
                            file_list += f", and {len(matching_files) - 5} more"
                        await speak_text(f"Found {len(matching_files)} files containing '{search_text}': {file_list}")
                    else:
                        await speak_text(f"No files containing '{search_text}' found")
                else:
                    await speak_text("No search text specified")
            elif action_name.startswith('get_time'):
                await speak_text(get_time())
            elif action_name.startswith('dictate'):
                dictated_text = action[len("dictate"):].strip()
                handle_dictate(dictated_text)
            else:
                logging.warning(f"Action '{normalized_action}' not recognized in the action list.")
                display.add_conversation(f"Unknown action: {action_name}")

        if text_to_speak:
            logging.info(f"Marvin says: {text_to_speak}")
            await speak_text(text_to_speak)

        # No need to explicitly call display.show() here as the window should already be visible
        # display.show()

async def set_timer(duration: str):
    global timer_counter
    try:
        logging.debug(f"Setting timer with duration: '{duration}'")
        
        # First, check if the duration is already in the format "X unit"
        duration_parts = duration.split()
        logging.debug(f"Duration parts: {duration_parts}")
        
        if len(duration_parts) == 2:
            # Format is already "X unit"
            try:
                value = int(duration_parts[0])
                unit_input = duration_parts[1].lower()
                logging.debug(f"Parsed as two parts: value={value}, unit={unit_input}")
            except ValueError as e:
                logging.error(f"Error parsing value: {e}")
                await speak_text('Invalid timer format. The value must be a number.')
                return
        else:
            # Try to parse the duration as a single value
            # Check if it's just a number (assume seconds)
            try:
                value = int(duration)
                unit_input = 'seconds'
                logging.debug(f"Parsed as single number: {value} {unit_input}")
            except ValueError:
                # Try to extract number and unit from a string without spaces
                import re
                match = re.match(r'(\d+)(\w+)', duration)
                if match:
                    try:
                        value = int(match.group(1))
                        unit_abbr = match.group(2).lower()
                        unit_input = unit_abbr
                        logging.debug(f"Parsed with regex: value={value}, unit={unit_input}")
                    except ValueError as e:
                        logging.error(f"Error parsing regex match: {e}")
                        await speak_text('Invalid timer format. Use format like "5 minutes" or "5m".')
                        return
                else:
                    logging.error(f"Could not parse timer format: '{duration}'")
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
            logging.debug(f"Mapped '{unit_input}' to '{unit}'")
        else:
            logging.error(f"Unknown time unit: '{unit_input}'")
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
            
            logging.debug(f"Setting timer for {value} {display_unit} ({seconds_value} seconds)")
            timer_name = f"timer_{timer_counter}"
            timer_counter += 1
            display.add_timer(timer_name, timedelta(seconds=seconds_value))
            await asyncio.sleep(seconds_value)
            display.remove_timer(timer_name)
            await speak_text('Timer complete!')
        else:
            # This should never happen with our mapping
            logging.error(f"Unexpected error: Unit '{unit}' not in valid_units after mapping")
            await speak_text('Invalid time unit. Use seconds, minutes, or hours.')
    except Exception as e:
        logging.error(f'Error setting timer: {e}', exc_info=True)
        await speak_text('Error setting timer.')

async def stop_timer():
    # Stop all active timers by removing each one from the display
    active_timers = list(display.timers.keys())
    for tname in active_timers:
        display.remove_timer(tname)
    logging.info('All timers stopped')

# Global variable to track the running event loop
assistant_loop = None
assistant_task = None

def start_assistant():
    global assistant_loop, assistant_task
    
    if assistant_loop is not None:
        logging.info('Assistant is already running')
        return
    
    # Start the system tray in a separate thread
    tray_thread = threading.Thread(target=create_system_tray, daemon=True)
    tray_thread.start()
    
    logging.info('Starting assistant...')
    assistant_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(assistant_loop)
    assistant_task = assistant_loop.create_task(async_main())
    assistant_loop.run_until_complete(assistant_task)

def stop_assistant():
    global assistant_loop, assistant_task
    
    if assistant_loop is None:
        logging.info('Assistant is not running')
        return

    try:
        assistant_task.cancel()
        logging.info('Stopping assistant...')
        
        # Give it a moment to clean up
        import time
        time.sleep(0.5)
        
        # Close the loop
        assistant_loop.close()
    except Exception as e:
        logging.error(f"Error stopping assistant: {e}")
    finally:
        assistant_loop = None
        assistant_task = None

# Function to create system tray icon
def create_system_tray():
    image = Image.open('icon.png')
    
    def on_exit(icon):
        logging.info('Exiting Marvin from system tray...')
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

def main():
    # Create a thread for the assistant
    assistant_thread = threading.Thread(target=start_assistant, daemon=True)
    assistant_thread.start()
    
    # Run the display GUI in the main thread
    display.run()

if __name__ == "__main__":
    main()