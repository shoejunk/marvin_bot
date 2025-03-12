import playsound
import time
import threading
from logger_config import get_logger

# Get a logger for this module
logger = get_logger(__name__)

def play_waiting_sound(stop_event):
    while not stop_event.is_set():
        playsound.playsound("waiting_sound.mp3", True)
        time.sleep(0.1)

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
        # Play in a separate thread to avoid blocking
        threading.Thread(target=lambda: playsound.playsound(sound_file, True), daemon=True).start()
    except Exception as e:
        logger.error(f"Error playing sound {sound_file}: {e}")
