import playsound
import time
import threading
from logger_config import get_logger
import platform
from ctypes import c_buffer, windll
from random import random

# Get a logger for this module
logger = get_logger(__name__)

def play_waiting_sound(stop_event):
    while not stop_event.is_set():
        playsound.playsound("waiting_sound.mp3", True)
        time.sleep(0.1)

def _play_sound_with_cleanup(sound_file):
    """
    Play a sound and properly clean up resources after playback.
    This is specifically for Windows to prevent LAV audio decoder instances from accumulating.
    
    Args:
        sound_file: Path to the sound file to play.
    """
    try:
        if platform.system() == 'Windows':
            # Windows implementation with proper cleanup
            from sys import getfilesystemencoding
            
            # Generate a unique alias for this sound
            alias = 'playsound_' + str(random())
            
            # Function to send MCI commands
            def win_command(*command):
                buf = c_buffer(255)
                command = ' '.join(command).encode(getfilesystemencoding())
                error_code = int(windll.winmm.mciSendStringA(command, buf, 254, 0))
                if error_code:
                    error_buffer = c_buffer(255)
                    windll.winmm.mciGetErrorStringA(error_code, error_buffer, 254)
                    logger.error(f"MCI Error {error_code} for command: {command.decode()}, {error_buffer.value.decode()}")
                return buf.value
            
            try:
                # Open and play the sound
                win_command('open "' + sound_file + '" alias', alias)
                win_command('set', alias, 'time format milliseconds')
                duration_ms = win_command('status', alias, 'length')
                win_command('play', alias, 'from 0 to', duration_ms.decode())
                
                # Wait for playback to complete
                time.sleep(float(duration_ms) / 1000.0)
            finally:
                # Always close the alias to clean up resources
                try:
                    win_command('close', alias)
                    logger.debug(f"Successfully closed sound alias: {alias}")
                except Exception as close_error:
                    logger.error(f"Error closing sound alias {alias}: {close_error}")
        else:
            # For non-Windows platforms, use the standard playsound
            playsound.playsound(sound_file, True)
    except Exception as e:
        logger.error(f"Error in _play_sound_with_cleanup for {sound_file}: {e}")

def play_waiting_sound_once(sound_file="waiting_sound.mp3"):
    """
    Play the waiting sound once in a separate thread to avoid blocking.
    This function is used when the wake word is recognized.
    
    Args:
        sound_file: Path to the sound file to play. If no extension is provided, .mp3 will be added.
    """
    try:
        # Add .mp3 extension if not already present
        if not sound_file.lower().endswith(('.mp3', '.wav')):
            sound_file = sound_file + ".mp3"
            
        logger.debug(f"Playing sound: {sound_file}")
        # Play in a separate thread to avoid blocking, but ensure cleanup happens
        threading.Thread(target=lambda: _play_sound_with_cleanup(sound_file), daemon=True).start()
    except Exception as e:
        logger.error(f"Error playing sound {sound_file}: {e}")
