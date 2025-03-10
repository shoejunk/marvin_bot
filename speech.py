import speech_recognition as sr
import time
from logger_config import get_logger

# Configure logging using the new thread-specific logger
logger = get_logger(__name__)

# Track consecutive failed attempts to dynamically adjust sensitivity
consecutive_failures = 0
MAX_CONSECUTIVE_FAILURES = 3
BASE_ENERGY_THRESHOLD = 300
ADJUSTED_ENERGY_THRESHOLD = 500

def transcribe_speech_to_text() -> str:
    global consecutive_failures
    
    logger.debug('Entering transcribe_speech_to_text function')
    recognizer = sr.Recognizer()
    source = None
    try:
        source = sr.Microphone()
        with source:
            logger.debug('Acquired microphone resource')
            
            # Adjust for ambient noise with a reasonable duration
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Dynamically adjust energy threshold based on consecutive failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                recognizer.energy_threshold = ADJUSTED_ENERGY_THRESHOLD
                logger.debug(f"Using higher energy threshold ({ADJUSTED_ENERGY_THRESHOLD}) after {consecutive_failures} consecutive failures")
            else:
                recognizer.energy_threshold = BASE_ENERGY_THRESHOLD
                logger.debug(f"Using standard energy threshold ({BASE_ENERGY_THRESHOLD})")
            
            # Increase the pause threshold significantly to wait longer for the user to finish speaking
            # Default is 0.8 seconds, increasing to 2.0 gives much more time to finish a sentence
            recognizer.pause_threshold = 2.0
            
            # Set a higher non-speaking duration to prevent premature cutoffs
            # This is the minimum length of silence after speech before considering the phrase complete
            recognizer.non_speaking_duration = 1.0
            
            logger.debug("Listening...")
            logger.debug('Starting speech recognition')
            
            # Use a longer timeout and add a generous phrase time limit
            # This prevents cutting off long sentences while still having a reasonable timeout
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)
            
            logger.debug('Speech recognition completed')
            
            text = recognizer.recognize_google(audio)
            logger.debug("You said: %s", text)
            
            # Reset consecutive failures counter on success
            consecutive_failures = 0
            return text
    except sr.UnknownValueError:
        logger.warning('Could not understand audio')
        # Increment failure counter but don't add delay
        consecutive_failures += 1
        return ""
    except sr.RequestError as e:
        logger.error('Speech recognition service error: %s', e)
        return ""
    except sr.WaitTimeoutError:
        logger.debug('No speech detected within timeout period')
        consecutive_failures += 1
        return ""
    except Exception as e:
        logger.error(f'Unexpected error in speech recognition: {e}')
        return ""
    finally:
        logger.debug('Speech recognition finished')
        if source is not None:
            try:
                source.__exit__(None, None, None)
            except AttributeError:
                pass
    logger.debug('Exiting transcribe_speech_to_text function')
    return ""
