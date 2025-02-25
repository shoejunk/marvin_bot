import playsound
import time

def play_waiting_sound(stop_event):
    while not stop_event.is_set():
        playsound.playsound("waiting_sound.mp3", True)
        time.sleep(0.1)
