"""
Голосовые функции (распознавание и синтез речи).
"""
import streamlit as st
import logging
from typing import Optional
from io import BytesIO

logger = logging.getLogger(__name__)


def recognize_speech_from_audio(audio_bytes: bytes) -> Optional[str]:
    try:
        import speech_recognition as sr
    except ImportError:
        st.warning("Установите SpeechRecognition: pip install SpeechRecognition")
        return None
    recognizer = sr.Recognizer()
    try:
        audio_file = BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language="ru-RU")
    except Exception as e:
        logger.warning(f"Ошибка распознавания речи: {e}")
        return None


def text_to_speech_mp3(text: str) -> Optional[bytes]:
    try:
        from gtts import gTTS
    except ImportError:
        st.warning("Установите gTTS: pip install gTTS")
        return None
    try:
        tts = gTTS(text=text, lang="ru", slow=False)
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        logger.warning(f"Ошибка синтеза речи: {e}")
        return None
