"""
Конфигурация и константы Audiobook Maker
"""

import os
from pathlib import Path

SAMPLE_RATE = 48000
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "."))

SPEAKERS = {
    "Ксения (женский)": "xenia",
    "Байя (женский)": "baya",
    "Ксения 2 (женский)": "kseniya",
    "Айдар (мужской)": "aidar",
    "Евгений (мужской)": "eugene",
}

FORMATS = {
    "MP3 (128 kbps)": {"format": "mp3", "ext": ".mp3", "params": {"bitrate": "128k"}},
    "MP3 (192 kbps)": {"format": "mp3", "ext": ".mp3", "params": {"bitrate": "192k"}},
    "MP3 (320 kbps)": {"format": "mp3", "ext": ".mp3", "params": {"bitrate": "320k"}},
    "WAV (без сжатия)": {"format": "wav", "ext": ".wav", "params": {}},
    "OGG Vorbis": {"format": "ogg", "ext": ".ogg", "params": {}},
}
