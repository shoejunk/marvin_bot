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

def play_waiting_sound_once():
    """
    Play the waiting sound once in a separate thread to avoid blocking.
    This function is used when the wake word is recognized.
    """
    try:
        logger.debug("Playing waiting sound")
        # Play in a separate thread to avoid blocking
        threading.Thread(target=lambda: playsound.playsound("waiting_sound.mp3", True), daemon=True).start()
    except Exception as e:
        logger.error(f"Error playing waiting sound: {e}")
