"""
streamlit run translation_webui.py -- --sound mic
"""
import streamlit as st
import whisper
from googletrans import Translator
import soundcard as sc
import threading
import queue
import numpy as np
import re
import argparse


SAMPLE_RATE = 16000
INTERVAL = 5
BUFFER_SIZE = 4096

parser = argparse.ArgumentParser()
parser.add_argument('--model', default='large')
parser.add_argument('--sound', default='speaker')
args = parser.parse_args()

print('Loading model...')
model = whisper.load_model(args.model)
print('Done')

q_audio = queue.Queue()
q_split = queue.Queue()
q_sentence = queue.Queue()
q_show = queue.Queue()
b = np.ones(100) / 100

options = whisper.DecodingOptions()


def recognize():
    while True:
        audio = q_audio.get()
        if (audio ** 2).max() > 0.001:
            audio = whisper.pad_or_trim(audio)

            # make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(model.device)

            # detect the spoken language
            _, probs = model.detect_language(mel)

            # decode the audio
            result = whisper.decode(model, mel, options)

            # print the recognized text
            print(f'{max(probs, key=probs.get)}: {result.text}')
            # if max(probs, key=probs.get) == "en":
            #     # with col_en:
            #     placeholder_en.write(result.text)
            # if max(probs, key=probs.get) == "ja":
            #     # with col_ja:
            #     placeholder_ja.write(result.text)

            # add to queue to split sentence
            q_split.put(result.text)


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
    while True:
        sentence = q_sentence.get()
        if sentence:
            # print("get: " + sentence)
            translator = Translator()
            lang = translator.detect(sentence).lang
            # 言語が日本語だったら
            if lang == "ja":
                trans_text = translator.translate(
                    sentence, src=lang, dest="en").text
                q_show.put(["ja", sentence, trans_text])
                # print("translate: " + trans_text)

            # 言語が英語だったら
            elif lang == "en":
                trans_text = translator.translate(
                    sentence, src=lang, dest="ja").text
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


th_recognize = threading.Thread(target=recognize, daemon=True)
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

# リフレッシュと同時になぜかモデルのロードが始まってVRAMが溢れて死ぬ。なんで、、、
# refresh_button = st.button("refresh")
st.header(args.sound + "mode")
col_en, col_ja = st.columns(2)
with col_en:
    st.header("en")
    placeholder_en = st.empty()
with col_ja:
    st.header("ja")
    placeholder_ja = st.empty()
ja_sentence = ""
en_sentence = ""
while True:
    d_list = q_show.get()
    la = d_list[0]

    if la == "ja":
        ja_sentence = ja_sentence + d_list[1] + "\n\n"
        en_sentence = en_sentence + d_list[2] + "\n\n"
        placeholder_ja.write(ja_sentence)
        placeholder_en.write(en_sentence)
        if d_list[1] == "チャットリセット":
            ja_sentence = ""
            en_sentence = ""
    elif la == "en":
        en_sentence = en_sentence + d_list[1] + "\n\n"
        ja_sentence = ja_sentence + d_list[2] + "\n\n"
        placeholder_en.write(en_sentence)
        placeholder_ja.write(ja_sentence)
        if d_list[1] == "chat reset":
            ja_sentence = ""
            en_sentence = ""

    # if refresh_button:
    #     ja_sentence = ""
    #     en_sentence = ""
    # else:
    #     pass
