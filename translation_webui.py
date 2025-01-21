import streamlit as st
from google.cloud import speech
from googletrans import Translator
import soundcard as sc
import threading
import queue
import numpy as np
import os
import re
import datetime

# Constants
SAMPLE_RATE = 16000
INTERVAL = 5
BUFFER_SIZE = 4096
b = np.ones(100) / 100

# Parse sound source
st.title("Real-Time Speech Transcription and Translation")
sound_source = st.selectbox("Select Sound Source:", ["speaker", "mic"])

# Set the environment variable for authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "composed-card-448514-q1-c3191fa38891.json"

# Queues for inter-thread communication
q_audio = queue.Queue()
q_split = queue.Queue()
q_sentence = queue.Queue()
q_show = queue.Queue()

# Thread flags
stop_flag = threading.Event()

# Logging directory
os.makedirs("log", exist_ok=True)


def transcribe_audio_with_language_detection(stop_flag):
    client = speech.SpeechClient()
    while not stop_flag.is_set():
        try:
            audio_pcm = q_audio.get(timeout=1)
            if not audio_pcm:
                print("Empty audio data received")  # Debugging statement
                continue
            print(f"Audio PCM size: {len(audio_pcm)}")  # Check audio data size

            audio_data = speech.RecognitionAudio(content=audio_pcm)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=SAMPLE_RATE,
                language_code="en-US",
                alternative_language_codes=["ja-JP"],
            )
            response = client.recognize(config=config, audio=audio_data)
            for result in response.results:
                if result.alternatives:
                    transcript = result.alternatives[0].transcript
                    print(f"Transcript: {transcript}")  # Debugging statement
                    q_split.put(transcript)
                else:
                    print("No alternatives found in response.")  # Debugging statement
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Transcription error: {e}")  # Debugging statement
            break


def split_sentences(stop_flag):
    """
    Split sentences from the transcription queue.
    """
    sentence_prev = ""
    while not stop_flag.is_set():
        try:
            sentence = q_split.get(timeout=1)
            sentence = sentence_prev + sentence
            sentence_prev = ""
            sentences = re.split("(?<=[。．.?？!！])", sentence)
            sentences = [s for s in sentences if s]
            for s in sentences:
                if re.search("[。．.?？!！]$", s):
                    q_sentence.put(s)
                else:
                    sentence_prev = s
        except queue.Empty:
            continue

def translation(stop_flag):
    """
    Translate sentences from the transcription queue using Google Translate.
    """
    translator = Translator()
    while not stop_flag.is_set():
        try:
            sentence = q_sentence.get(timeout=1)
            lang = translator.detect(sentence).lang  # Detect the language
            if lang == "ja":
                trans_text = translator.translate(sentence, src="ja", dest="en").text
                q_show.put(["ja", sentence, trans_text])
            elif lang == "en":
                trans_text = translator.translate(sentence, src="en", dest="ja").text
                q_show.put(["en", sentence, trans_text])
            print(f"Queued translation: {sentence} -> {trans_text}") # Debugging statement
        except queue.Empty:
            continue
        except Exception as e:
            st.error(f"Translation error: {e}")


def record_audio(stop_flag):
    import comtypes  # Import within the function to avoid global initialization
    comtypes.CoInitialize()  # Initialize COM for this thread

    try:
        mic = (
            sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)
            if sound_source == "speaker"
            else sc.get_microphone(id=str(sc.default_microphone().name))
        )
        with mic.recorder(samplerate=SAMPLE_RATE, channels=1) as recorder:
            audio_buffer = np.empty(SAMPLE_RATE * INTERVAL, dtype=np.float32)
            print(f"Audio buffer length: {len(audio_buffer)}")  # Debugging statement
            while not stop_flag.is_set():
                try:
                    # Read audio data
                    audio_data = recorder.record(BUFFER_SIZE)
                    audio_data = audio_data[:, 0]  # Ensure it's a 1D array
                    audio_buffer = np.concatenate([audio_buffer[len(audio_data):], audio_data])
                    # Convert to 16-bit PCM
                    audio_pcm = (audio_buffer * 32767).astype(np.int16).tobytes()
                    if audio_pcm:
                        print("Captured audio data")  # Debugging statement
                        q_audio.put(audio_pcm)
                except Exception as e:
                    print(f"Audio recording error: {e}")
                    break
    finally:
        # Ensure COM is uninitialized when the thread exits
        comtypes.CoUninitialize()
            

# UI Components
refresh_button = st.button("Refresh")
start_button = st.button("Start Transcription")
stop_button = st.button("Stop Transcription")

col_en, col_ja = st.columns(2)
with col_en:
    st.header("English")
    placeholder_en = st.empty()
with col_ja:
    st.header("日本語")
    placeholder_ja = st.empty()

# Sentence logs
t = str(datetime.datetime.now().replace(microsecond=0)).replace(" ", "_").replace(":", "-")
path_ja = f"log/{t}_ja.txt"
path_en = f"log/{t}_en.txt"
ja_sentence = ""
en_sentence = ""

if start_button:
    stop_flag.clear()
    print("Starting threads...")
    threading.Thread(target=record_audio, args=(stop_flag,), daemon=True).start()
    threading.Thread(target=transcribe_audio_with_language_detection, args=(stop_flag,), daemon=True).start()
    threading.Thread(target=split_sentences, args=(stop_flag,), daemon=True).start()
    threading.Thread(target=translation, args=(stop_flag,), daemon=True).start()
    st.success("Transcription started.")
    print("All threads started.")

if stop_button:
    stop_flag.set()
    st.warning("Transcription stopped.")

if refresh_button:
    ja_sentence = ""
    en_sentence = ""


while not stop_flag.is_set():
    try:
        # Get the transcription result from the queue
        d_list = q_show.get(timeout=1)
        print(f"Translation output: {d_list}")  # Debugging statement
        
        lang, original, translated = d_list

        # Displaying transcription in the Streamlit UI
        if lang == "ja":
            ja_sentence = f"{original}\n\n{ja_sentence}"
            en_sentence = f"{translated}\n\n{en_sentence}"

            # Avoid redundant transcription by checking if the sentence has been added already
            if original not in ja_sentence:
                with open(path_ja, "a", encoding="utf-8") as f:
                    f.write(original + "\n")
            if translated not in en_sentence:
                with open(path_en, "a", encoding="utf-8") as f:
                    f.write(translated + "\n")

        elif lang == "en":
            en_sentence = f"{original}\n\n{en_sentence}"
            ja_sentence = f"{translated}\n\n{ja_sentence}"

            # Avoid redundant transcription by checking if the sentence has been added already
            if translated not in ja_sentence:
                with open(path_ja, "a", encoding="utf-8") as f:
                    f.write(translated + "\n")
            if original not in en_sentence:
                with open(path_en, "a", encoding="utf-8") as f:
                    f.write(original + "\n")

        # Display the transcriptions in Streamlit
        placeholder_ja.write(ja_sentence)
        placeholder_en.write(en_sentence)

    except queue.Empty:
        continue
