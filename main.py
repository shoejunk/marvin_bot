#!/usr/bin/env python3
"""
main.py - Main entry point for the voice assistant.
Processes voice input, obtains AI responses, strips out <action> tags before speaking,
and triggers actions (e.g., turning lights on/off) via the MerossController.
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
from datetime import timedelta
import pystray
from PIL import Image
import threading
import logging

# Add global timer control variable
timer_active = False

logging.basicConfig(level=logging.DEBUG)

async def async_main():
    logging.debug("System prompt: %s", system_prompt)
    logging.debug("Initializing Meross Controller...")
    meross_controller = await MerossController.init()
    spotify_client = SpotifyClient()
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
            if any(normalized_action.startswith(action) for action in action_strings):
                logging.info(f"Detected action: {normalized_action}")
                if normalized_action.startswith("turn_on_light"):
                    await meross_controller.turn_on_light()
                elif normalized_action.startswith("turn_off_light"):
                    await meross_controller.turn_off_light()
                elif normalized_action.startswith("play_song"):
                    song_name = normalized_action.split(':', 1)[1].strip() if ':' in normalized_action else ''
                    if song_name:
                        spotify_client.play_track(song_name)
                elif normalized_action.startswith("play_playlist"):
                    playlist_name = normalized_action.split(':', 1)[1].strip() if ':' in normalized_action else ''
                    if playlist_name:
                        spotify_client.play_playlist(playlist_name)
                elif normalized_action.startswith("pause_music"):
                    spotify_client.pause_music()
                elif normalized_action.startswith("unpause_music"):
                    spotify_client.unpause_music()
                elif normalized_action.startswith("volume_up"):
                    # Check if there's a specified increment value
                    increment = 10  # Default increment value
                    if ':' in normalized_action:
                        try:
                            increment = int(normalized_action.split(':', 1)[1].strip())
                        except ValueError:
                            pass
                    spotify_client.volume_up(increment)
                elif normalized_action.startswith("volume_down"):
                    # Check if there's a specified decrement value
                    decrement = 10  # Default decrement value
                    if ':' in normalized_action:
                        try:
                            decrement = int(normalized_action.split(':', 1)[1].strip())
                        except ValueError:
                            pass
                    spotify_client.volume_down(decrement)
                elif normalized_action.startswith("reboot"):
                    await speak_text("Marvin rebooting")
                    logging.info("Rebooting Marvin...")
                    bat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "run_marvin.bat"))
                    logging.info(f"Running batch file: {bat_path}")
                    subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                    os._exit(0)
                elif normalized_action.startswith('set_timer'):
                    duration = normalized_action.split(':', 1)[1].strip() if ':' in normalized_action else ''
                    if duration:
                        asyncio.create_task(set_timer(duration))
                elif normalized_action.startswith('stop_timer'):
                    await stop_timer()
                elif normalized_action.startswith('shut_down'):
                    await speak_text('Shutting down Marvin')
                    logging.info('Shutting down Marvin...')
                    stop_assistant()
                    os._exit(0)
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
    menu = (
        pystray.MenuItem('Start', lambda: start_assistant()),
        pystray.MenuItem('Stop', lambda: stop_assistant()),
        pystray.MenuItem('Exit', lambda: icon.stop())
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