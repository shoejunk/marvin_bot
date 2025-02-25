from pydub import AudioSegment
from pydub.playback import play
import os
import edge_tts

default_voice = "en-GB-RyanNeural"

async def speak_text(text: str, voice=default_voice, gain_db=10):
    tts_file = "temp_tts.mp3"
    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(tts_file)

    # Load the audio file
    audio = AudioSegment.from_file(tts_file, format="mp3")
    
    # Increase volume by gain_db decibels
    louder_audio = audio + gain_db

    # Play the louder audio
    play(louder_audio)
    
    try:
        os.remove(tts_file)
    except FileNotFoundError:
        pass  # Ignore if the file doesn't exist
