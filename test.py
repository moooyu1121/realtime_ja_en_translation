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
audio_path = "Recording_resampled.wav"
transcribe_audio(audio_path)
