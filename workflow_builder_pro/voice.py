"""
Голосовые функции: распознавание и синтез речи
"""
from io import BytesIO
from typing import Optional

from utils import logger

# Голосовые библиотеки
try:
    import speech_recognition as sr
    from gtts import gTTS
    VOICE_SUPPORT = True
except ImportError:
    VOICE_SUPPORT = False
    sr = None
    gTTS = None


def recognize_speech_from_audio(audio_bytes: bytes) -> Optional[str]:
    """Распознавание русской речи из аудиобайтов"""
    if not VOICE_SUPPORT or sr is None:
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
    """Генерация MP3 из текста (русский язык)"""
    if not VOICE_SUPPORT or gTTS is None:
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
