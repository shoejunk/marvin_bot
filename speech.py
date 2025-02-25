import speech_recognition as sr
import logging

logging.basicConfig(level=logging.DEBUG)

def transcribe_speech_to_text() -> str:
    logging.debug('Entering transcribe_speech_to_text function')
    recognizer = sr.Recognizer()
    source = None
    try:
        source = sr.Microphone()
        with source:
            logging.debug('Acquired microphone resource')
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logging.debug("Listening...")
            logging.debug('Starting speech recognition')
            audio = recognizer.listen(source)
            logging.debug('Speech recognition completed')
            text = recognizer.recognize_google(audio)
            logging.debug("You said: %s", text)
            return text
    except sr.UnknownValueError:
        logging.warning('Could not understand audio')
        return ""
    except sr.RequestError as e:
        logging.error('Speech recognition service error: %s', e)
        logging.error("Error with the speech recognition service: %s", e)
        return ""
    finally:
        logging.debug('Speech recognition finished')
        if source is not None:
            try:
                source.__exit__(None, None, None)
            except AttributeError:
                pass
    logging.debug('Exiting transcribe_speech_to_text function')
