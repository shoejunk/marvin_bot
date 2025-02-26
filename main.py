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
from conversation_history import update_history
from spotify import SpotifyClient
from file_operations import FileOperations  # Import the new FileOperations class
from datetime import timedelta
import pystray
from PIL import Image
import threading
import logging
import json

# Add global timer control variable
timer_active = False

logging.basicConfig(level=logging.DEBUG)

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
        update_history(user_input, reply)

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
            else:
                logging.info(f"Detected action: {action_name}")
            
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
            elif action_name.startswith('set_timer'):
                duration = params[0] if params else ''
                if duration:
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
            else:
                logging.warning(f"Action '{normalized_action}' not recognized in the action list.")

        if text_to_speak:
            logging.info(f"Marvin says: {text_to_speak}")
            await speak_text(text_to_speak)

async def set_timer(duration: str):
    global timer_active
    try:
        # Normalize duration string (replace underscores with spaces)
        duration = duration.replace('_', ' ')

        # Parse duration string
        time_parts = {'h': 0, 'm': 0, 's': 0}
        parts = duration.split()
        for i in range(0, len(parts), 2):
            if i+1 >= len(parts):
                break
            value = int(parts[i])
            unit = parts[i+1][0].lower()
            if unit == 'h':
                time_parts['h'] = value
            elif unit == 'm':
                time_parts['m'] = value
            elif unit == 's':
                time_parts['s'] = value

        total_seconds = time_parts['h'] * 3600 + time_parts['m'] * 60 + time_parts['s']
        logging.info(f'Timer set for {total_seconds} seconds')
        await asyncio.sleep(total_seconds)

        # Initialize pygame mixer and play waiting sound on loop
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load('waiting_sound.mp3')
        pygame.mixer.music.play(-1)  # -1 means loop indefinitely
        timer_active = True
        logging.info('Playing waiting sound on loop')
    except Exception as e:
        logging.error(f'Error setting timer: {e}')

async def stop_timer():
    global timer_active
    if timer_active:
        import pygame
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        timer_active = False
        logging.info('Timer stopped')

# Global variable to track the running event loop
assistant_loop = None
assistant_task = None

def start_assistant():
    global assistant_loop, assistant_task
    if assistant_loop is not None:
        logging.info('Assistant is already running')
        return

    assistant_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(assistant_loop)
    assistant_task = assistant_loop.create_task(async_main())
    logging.info('Starting assistant...')
    try:
        assistant_loop.run_until_complete(assistant_task)
    except asyncio.CancelledError:
        logging.info('Assistant stopped')
    finally:
        assistant_loop.close()
        assistant_loop = None
        assistant_task = None

def stop_assistant():
    global assistant_loop, assistant_task
    if assistant_loop is None:
        logging.info('Assistant is not running')
        return

    assistant_task.cancel()
    logging.info('Stopping assistant...')

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

# Start the system tray in a separate thread
tray_thread = threading.Thread(target=create_system_tray)
tray_thread.daemon = True
tray_thread.start()

def main():
    start_assistant()

if __name__ == "__main__":
    main()