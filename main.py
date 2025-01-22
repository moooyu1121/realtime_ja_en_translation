from google.cloud import speech
from googletrans import Translator
import streamlit as st
import os
import soundcard as sc
import io
import wave
import numpy as np
import threading
import queue
import asyncio

# Set the environment variable for authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "composed-card-448514-q1-c3191fa38891.json"

SAMPLE_RATE = 16000
INTERVAL = 5
BUFFER_SIZE = 4096

# sound_source = "speaker"
sound_source = "mic"

def transcribe_audio():
    """
    Transcribe audio using Google Speech-to-Text API.
    """
    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # Change if your file has a different encoding
                sample_rate_hertz=SAMPLE_RATE,  # Update if your file has a different sample rate
                language_code="ja-JP",  # Set the language of the audio
                alternative_language_codes= ["en-US"],
                enable_automatic_punctuation=True
                )
    # print(config)
    while True:
        content = q_audio.get()
        audio = speech.RecognitionAudio(content=content)
        response = client.recognize(config=config, audio=audio)
        # Print the transcriptions
        for result in response.results:
            print(f"{result.language_code}: {result.alternatives[0].confidence:.2f}: {result.alternatives[0].transcript}")
            text = result.alternatives[0].transcript
            lang = result.language_code
            asyncio.run(translation_text(text, lang))


async def translation_text(text, lang):
    """
    Translate sentences from the text and language info.
    """
    translator = Translator()
    # while True:
    # text, lang = await asyncio.to_thread(q_text.get)  # 非同期でキューから取得
    if lang == "ja-jp":
        result = await translator.translate(text, src="ja", dest="en")
        en_text = result.text
        ja_text = text
        q_show.put((ja_text, en_text))
    elif lang == "en-us":
        result = await translator.translate(text, src="en", dest="ja")
        ja_text = result.text
        en_text = text
        q_show.put((ja_text, en_text))


def numpy_to_wav(audio_data, sample_rate):
    """Convert numpy array to WAV byte data."""
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(1)  # モノラル
            wav_file.setsampwidth(2)  # 16ビットPCM
            wav_file.setframerate(sample_rate)
            wav_file.writeframes((audio_data * 32767).astype(np.int16).tobytes())
        return wav_io.getvalue()


def audio_record():
    # start recording
    mic = (
            sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)
            if sound_source == "speaker"
            else sc.get_microphone(id=str(sc.default_microphone().name))
        )
    print(mic)
    b = np.ones(100) / 100
    with mic.recorder(samplerate=SAMPLE_RATE, channels=1) as recorder:
        audio = np.empty(SAMPLE_RATE * INTERVAL + BUFFER_SIZE, dtype=np.float32)
        n = 0
        while True:
            while n < SAMPLE_RATE * INTERVAL:
                data = recorder.record(BUFFER_SIZE)
                audio[n:n+len(data)] = data.reshape(-1)
                n += len(data)

            # find silent periods
            m = n * 4 // 5
            vol = np.convolve(audio[m:n] ** 2, b, 'same')
            m += vol.argmin()

            if (audio[:m] ** 2).max() > 0.01:
                # Convert audio to WAV format and put into queue
                wav_data = numpy_to_wav(audio[:m], SAMPLE_RATE)
                q_audio.put(wav_data)

            audio_prev = audio
            audio = np.empty(SAMPLE_RATE * INTERVAL + BUFFER_SIZE, dtype=np.float32)
            audio[:n-m] = audio_prev[m:n]
            n = n-m


def show():
    """
    Display the translated text on cmd.
    """
    while True:
        try:
            ja_text, en_text = q_show.get()
            # st.write(f"Japanese: {ja_text}")
            # st.write(f"English: {en_text}")
            print(f"Japanese: {ja_text}")
            print(f"English: {en_text}")
        except queue.Empty:
            continue


def main():
    """
    Orchestrates the translation_text task and the main thread for audio processing.
    """
    # メインスレッドで翻訳結果の表示を動かす
    st.set_page_config(layout="wide")
    # refresh_button = st.button("Refresh")
    
    col_en, col_ja = st.columns(2)
    with col_en:
        st.caption("English")
        placeholder_en = st.empty()
    with col_ja:
        st.caption("日本語")
        placeholder_ja = st.empty()

    ja_sentence = ""
    en_sentence = ""

    while True:
        ja_text, en_text = q_show.get()

        ja_sentence = ja_text + "\n\n" + ja_sentence
        en_sentence = en_text + "\n\n" + en_sentence
        placeholder_ja.write(ja_sentence)
        placeholder_en.write(en_sentence)

        # if refresh_button:
        #     # Refreshボタンが押された場合に内容をリセット
        #     ja_sentence = ""
        #     en_sentence = ""
        #     t = str(datetime.datetime.now().replace(microsecond=0))
        #     t = t.replace(" ", "_")
        #     t = t.replace(":", "-")
        #     path_ja = "log/" + t + "_ja.txt"
        #     path_en = "log/" + t + "_en.txt"
        #     refresh_button = False
        # else:
        #     pass


if __name__ == "__main__":
    q_audio = queue.Queue()
    q_show = queue.Queue()

    # スレッドで音声処理と翻訳結果の表示を動かす
    th_transcribe = threading.Thread(target=transcribe_audio, daemon=True)
    th_transcribe.start()
    th_record = threading.Thread(target=audio_record, daemon=True)
    th_record.start()

    # asyncio.run(main())
    main()

    
