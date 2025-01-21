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
    """
    Transcribe audio and detect the language using Google Speech-to-Text API.
    """
    client = speech.SpeechClient()
    while not stop_flag.is_set():
        try:
            audio = q_audio.get(timeout=1)
            if (audio ** 2).max() > 0.001:
                content = audio.tobytes()
                # Configure the audio and recognition settings
                audio_data = speech.RecognitionAudio(content=content)
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=SAMPLE_RATE,
                    language_code="en-US",
                    alternative_language_codes=["ja-JP"],
                )
                # Perform the transcription
                response = client.recognize(config=config, audio=audio_data)
                for result in response.results:
                    transcript = result.alternatives[0].transcript
                    q_split.put(transcript)
        except queue.Empty:
            continue
        except Exception as e:
            st.error(f"Error during transcription: {e}")
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
        except queue.Empty:
            continue
        except Exception as e:
            st.error(f"Translation error: {e}")

def record_audio(stop_flag):
    """
    Record audio from the selected sound source.
    """
    mic = (
        sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)
        if sound_source == "speaker"
        else sc.get_microphone(id=str(sc.default_microphone().name))
    )
    with mic.recorder(samplerate=SAMPLE_RATE, channels=1) as recorder:
        audio = np.empty(SAMPLE_RATE * INTERVAL + BUFFER_SIZE, dtype=np.float32)
        n = 0
        while not stop_flag.is_set():
            while n < SAMPLE_RATE * INTERVAL:
                data = recorder.record(BUFFER_SIZE)
                audio[n:n + len(data)] = data.reshape(-1)
                n += len(data)
            q_audio.put(audio[:n])
            audio = np.empty(SAMPLE_RATE * INTERVAL + BUFFER_SIZE, dtype=np.float32)
            n = 0

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
    threading.Thread(target=record_audio, args=(stop_flag,), daemon=True).start()
    threading.Thread(target=transcribe_audio_with_language_detection, args=(stop_flag,), daemon=True).start()
    threading.Thread(target=split_sentences, args=(stop_flag,), daemon=True).start()
    threading.Thread(target=translation, args=(stop_flag,), daemon=True).start()
    st.success("Transcription started.")

if stop_button:
    stop_flag.set()
    st.warning("Transcription stopped.")

if refresh_button:
    ja_sentence = ""
    en_sentence = ""

while not stop_flag.is_set():
    try:
        d_list = q_show.get(timeout=1)
        lang, original, translated = d_list
        if lang == "ja":
            ja_sentence = f"{original}\n\n{ja_sentence}"
            en_sentence = f"{translated}\n\n{en_sentence}"
            with open(path_ja, "a", encoding="utf-8") as f:
                f.write(original + "\n")
            with open(path_en, "a", encoding="utf-8") as f:
                f.write(translated + "\n")
        elif lang == "en":
            en_sentence = f"{original}\n\n{en_sentence}"
            ja_sentence = f"{translated}\n\n{ja_sentence}"
            with open(path_ja, "a", encoding="utf-8") as f:
                f.write(translated + "\n")
            with open(path_en, "a", encoding="utf-8") as f:
                f.write(original + "\n")
        placeholder_ja.write(ja_sentence)
        placeholder_en.write(en_sentence)
    except queue.Empty:
        continue
