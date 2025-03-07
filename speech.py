import speech_recognition as sr
import logging
import os

# Use getLogger instead of basicConfig to avoid conflicts with main.py
logger = logging.getLogger(__name__)

# Only add handlers if they don't exist already
if not logger.handlers:
    try:
        # Set the logging level
        logger.setLevel(logging.DEBUG)
        
        # Create a stream handler for console output
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
        # Try to add file handler only if we can access the file
        log_file = "marvin.log"
        if not os.path.exists(log_file) or os.access(log_file, os.W_OK):
            file_handler = logging.FileHandler(log_file, delay=True)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up complete logging for {__name__}: {e}")

def transcribe_speech_to_text() -> str:
    logger.debug('Entering transcribe_speech_to_text function')
    recognizer = sr.Recognizer()
    source = None
    try:
        source = sr.Microphone()
        with source:
            logger.debug('Acquired microphone resource')
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.debug("Listening...")
            logger.debug('Starting speech recognition')
            audio = recognizer.listen(source)
            logger.debug('Speech recognition completed')
            text = recognizer.recognize_google(audio)
            logger.debug("You said: %s", text)
            return text
    except sr.UnknownValueError:
        logger.warning('Could not understand audio')
        return ""
    except sr.RequestError as e:
        logger.error('Speech recognition service error: %s', e)
        logger.error("Error with the speech recognition service: %s", e)
        return ""
    finally:
        logger.debug('Speech recognition finished')
        if source is not None:
            try:
                source.__exit__(None, None, None)
            except AttributeError:
                pass
    logger.debug('Exiting transcribe_speech_to_text function')
