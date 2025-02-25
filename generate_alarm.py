import wave
import math
import struct

# Parameters
sample_rate = 44100  # CD quality
frequency = 880      # A5 note
duration = 1.0       # 1 second
volume = 0.5         # 50% volume

# Generate sine wave
def generate_tone(freq, duration, volume):
    num_samples = int(sample_rate * duration)
    samples = []
    for i in range(num_samples):
        value = math.sin(2 * math.pi * freq * (i / sample_rate))
        samples.append(volume * value)
    return samples

# Create WAV file
def create_wav_file(filename, samples):
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        for sample in samples:
            wav_file.writeframes(struct.pack('h', int(sample * 32767.0)))

# Generate and save the alarm sound
tone = generate_tone(frequency, duration, volume)
create_wav_file('alarm.wav', tone)
