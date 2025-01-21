from google.cloud import speech
import os

# Set the environment variable for authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "composed-card-448514-q1-c3191fa38891.json"

def transcribe_audio(audio_file_path):
    """
    Transcribe audio using Google Speech-to-Text API.
    
    Parameters:
        audio_file_path (str): Path to the audio file.
    """
    client = speech.SpeechClient()

    # Read the audio file
    with open(audio_file_path, "rb") as audio_file:
        content = audio_file.read()

    # Configure the audio and recognition settings
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # Change if your file has a different encoding
        sample_rate_hertz=16000,  # Update if your file has a different sample rate
        language_code="ja-JP",  # Set the language of the audio
    )

    # Perform the transcription
    response = client.recognize(config=config, audio=audio)
    print(response)

    # Print the transcriptions
    for result in response.results:
        print("Transcript:", result.alternatives[0].transcript)

# Example usage
# audio_path = "Recording_resampled.wav"
# transcribe_audio(audio_path)


import soundcard as sc
import numpy as np

mic = sc.default_microphone()
with mic.recorder(samplerate=16000, channels=1) as recorder:
    audio_data = recorder.record(16000)
    print(f"Captured audio: {audio_data[:10]}")

# get a list of all speakers:
speakers = sc.all_speakers()
print("-----------------------\n")
print(type(speakers))
print(speakers)

# get the current default speaker on your system:
default_speaker = sc.default_speaker()
print("-----------------------\n")
print(type(default_speaker))
print(default_speaker)

# get a list of all microphones:
mics = sc.all_microphones()
print("-----------------------\n")
print(type(mics))
print(mics)

# get the current default microphone on your system:
default_mic = sc.default_microphone()
print("-----------------------\n")
print(type(default_mic))
print(default_mic)

import soundcard as sc

import numpy

fs = 16000
recording_sec = 5

default_speaker = sc.default_speaker()
default_mic = sc.default_microphone()

# record and play back one second of audio:
print("Recording...")
data = default_mic.record(samplerate=fs, numframes=fs*recording_sec)
print("Playing...")
default_speaker.play(data/numpy.max(data), samplerate=fs)
print("Done.")