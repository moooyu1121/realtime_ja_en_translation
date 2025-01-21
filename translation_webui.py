"""
streamlit run translation_webui.py -- --sound speaker
streamlit run translation_webui.py -- --sound mic
"""
import streamlit as st
from google.cloud import speech
from googletrans import Translator
import soundcard as sc
import keyboard
import datetime
import threading
import queue
import numpy as np
import re
import os
import argparse


SAMPLE_RATE = 16000
INTERVAL = 5
BUFFER_SIZE = 4096

parser = argparse.ArgumentParser()
parser.add_argument('--sound', default='speaker')
args = parser.parse_args()

# Set the environment variable for authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "composed-card-448514-q1-c3191fa38891.json"
print('sound source: ' + args.sound)

q_audio = queue.Queue()
q_split = queue.Queue()
q_sentence = queue.Queue()
q_show = queue.Queue()
b = np.ones(100) / 100

os.makedirs("log", exist_ok=True)


def transcribe_audio_with_language_detection():
    """
    Transcribe audio and detect the language using Google Speech-to-Text API.
    """
    client = speech.SpeechClient()
    while True:
        audio = q_audio.get()
        if (audio ** 2).max() > 0.001:
            content = audio.tobytes()
            # Configure the audio and recognition settings
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # Change if your file has a different encoding
                sample_rate_hertz=16000,  # Update if your file has a different sample rate
                language_code="en-US",  # Primary language (optional, for biasing results)
                alternative_language_codes=["ja-JP"],  # Other languages to detect
            )

            # Perform the transcription
            response = client.recognize(config=config, audio=audio)

            # Print the transcriptions and detected language
            for result in response.results:
                transcript = result.alternatives[0].transcript
                confidence = result.alternatives[0].confidence
                detected_language = result.language_code  # Detected language
                print(f'{detected_language, confidence:.2f}: {transcript}')
            
            # add to queue to split sentence
            # if detected_language == "en-US" or detected_language == "ja-JP":
            q_split.put(transcript)


def split_sentences_speaker():
    sentence_prev = ""
    while True:
        sentence = q_split.get()
        if sentence:
            sentence = sentence_prev + sentence
            sentence_prev = ""
            sentences = re.split("(?<=[。．.?？!！])", sentence)
            sentences = list(filter(lambda x: x != "", sentences))
            # print(list(sentences))
            for s in sentences:
                if s[-1] == "。" or s[-1] == "．" or s[-1] == "." or s[-1] == "?"\
                        or s[-1] == "？" or s[-1] == "!" or s[-1] == "！":
                    q_sentence.put(s)
                    sentence_prev = ""
                else:
                    sentence_prev = s


def split_sentences_mic():
    while True:
        sentence = q_split.get()
        if sentence:
            q_sentence.put(sentence)


def translation():
    """
    split sentence queue から文章を受け取り，google translation apiへ渡して翻訳
    [言語，元文，翻訳文]を1つのリストとしてキューに追加
    """
    while True:
        sentence = q_sentence.get()
        if sentence:
            # print("get: " + sentence)
            translator = Translator()
            lang = translator.detect(sentence).lang  # type: ignore
            # 言語が日本語だったら
            if lang == "ja":
                trans_text = translator.translate(
                    sentence, src=lang, dest="en").text  # type: ignore
                q_show.put(["ja", sentence, trans_text])
                # print("translate: " + trans_text)

            # 言語が英語だったら
            elif lang == "en":
                trans_text = translator.translate(
                    sentence, src=lang, dest="ja").text  # type: ignore
                q_show.put(["en", sentence, trans_text])
                # print("translate: " + trans_text)


def record():
    # start recording
    if args.sound == "speaker":
        with sc.get_microphone(id=str(sc.default_speaker().name),
                               include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            audio = np.empty(SAMPLE_RATE * INTERVAL +
                             BUFFER_SIZE, dtype=np.float32)
            n = 0
            while True:
                while n < SAMPLE_RATE * INTERVAL:
                    data = mic.record(BUFFER_SIZE)
                    audio[n:n+len(data)] = data.reshape(-1)
                    n += len(data)

                # find silent periods
                m = n * 4 // 5
                vol = np.convolve(audio[m:n] ** 2, b, 'same')
                m += vol.argmin()
                q_audio.put(audio[:m])

                audio_prev = audio
                audio = np.empty(SAMPLE_RATE * INTERVAL +
                                 BUFFER_SIZE, dtype=np.float32)
                audio[:n-m] = audio_prev[m:n]
                n = n-m

    elif args.sound == "mic":
        with sc.get_microphone(id=str(sc.default_microphone().name),
                               include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            audio = np.empty(SAMPLE_RATE * INTERVAL +
                             BUFFER_SIZE, dtype=np.float32)
            n = 0
            while True:
                while n < SAMPLE_RATE * INTERVAL:
                    data = mic.record(BUFFER_SIZE)
                    audio[n:n+len(data)] = data.reshape(-1)
                    n += len(data)

                # find silent periods
                m = n * 4 // 5
                vol = np.convolve(audio[m:n] ** 2, b, 'same')
                m += vol.argmin()
                q_audio.put(audio[:m])

                audio_prev = audio
                audio = np.empty(SAMPLE_RATE * INTERVAL +
                                 BUFFER_SIZE, dtype=np.float32)
                audio[:n-m] = audio_prev[m:n]
                n = n-m

    else:
        print("sound source input is not valid. Use speaker sound...")
        with sc.get_microphone(id=str(sc.default_speaker().name),
                               include_loopback=True).recorder(samplerate=SAMPLE_RATE, channels=1) as mic:
            audio = np.empty(SAMPLE_RATE * INTERVAL +
                             BUFFER_SIZE, dtype=np.float32)
            n = 0
            while True:
                while n < SAMPLE_RATE * INTERVAL:
                    data = mic.record(BUFFER_SIZE)
                    audio[n:n+len(data)] = data.reshape(-1)
                    n += len(data)

                # find silent periods
                m = n * 4 // 5
                vol = np.convolve(audio[m:n] ** 2, b, 'same')
                m += vol.argmin()
                q_audio.put(audio[:m])

                audio_prev = audio
                audio = np.empty(SAMPLE_RATE * INTERVAL +
                                 BUFFER_SIZE, dtype=np.float32)
                audio[:n-m] = audio_prev[m:n]
                n = n-m


th_recognize = threading.Thread(target=transcribe_audio_with_language_detection, daemon=True)
if args.sound == "speaker":
    th_split = threading.Thread(target=split_sentences_speaker, daemon=True)
elif args.sound == "mic":
    th_split = threading.Thread(target=split_sentences_mic, daemon=True)
else:
    print("sound source input is not valid. Use speaker sound...")
    th_split = threading.Thread(target=split_sentences_speaker, daemon=True)
th_translate = threading.Thread(target=translation, daemon=True)
th_record = threading.Thread(target=record, daemon=True)

th_recognize.start()
th_split.start()
th_translate.start()
th_record.start()


refresh_button = st.button("refresh")
col_en, col_ja = st.columns(2)
with col_en:
    st.header("English")
    placeholder_en = st.empty()
with col_ja:
    st.header("日本語")
    placeholder_ja = st.empty()
t = str(datetime.datetime.now().replace(microsecond=0))
t = t.replace(" ", "_")
t = t.replace(":", "-")
path_ja = "log/" + t + "_ja.txt"
path_en = "log/" + t + "_en.txt"

ja_sentence = ""
en_sentence = ""

while True:
    d_list = q_show.get()
    la = d_list[0]

    if la == "ja":
        ja_sentence = d_list[1] + "\n\n" + ja_sentence
        en_sentence = d_list[2] + "\n\n" + en_sentence
        placeholder_ja.write(ja_sentence)
        placeholder_en.write(en_sentence)
        f_ja = open(path_ja, "a")
        f_ja.write(d_list[1] + "\n")
        f_ja.close()
        f_en = open(path_en, "a")
        f_en.write(d_list[2] + "\n")
        f_en.close()
    elif la == "en":
        en_sentence = d_list[1] + "\n\n" + en_sentence
        ja_sentence = d_list[2] + "\n\n" + ja_sentence
        placeholder_en.write(en_sentence)
        placeholder_ja.write(ja_sentence)
        f_ja = open(path_ja, "a", encoding='UTF-8')
        f_ja.write(d_list[2] + "\n")
        f_ja.close()
        f_en = open(path_en, "a", encoding='UTF-8')
        f_en.write(d_list[1] + "\n")
        f_en.close()

    if keyboard.is_pressed("end"):
        ja_sentence = ""
        en_sentence = ""
        t = str(datetime.datetime.now().replace(microsecond=0))
        t = t.replace(" ", "_")
        t = t.replace(":", "-")
        path_ja = "log/" + t + "_ja.txt"
        path_en = "log/" + t + "_en.txt"

    if refresh_button:
        ja_sentence = ""
        en_sentence = ""
    else:
        pass
