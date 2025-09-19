from __future__ import annotations

"""Static configuration values for the utility plugin."""

from hikari import Color


# Embed colors
INFO_COLOR = Color(0x5865F2)
AVATAR_COLOR = Color(0x9932CC)
TIMESTAMP_COLOR = Color(0x00CED1)
COLOR_TOOL_COLOR = Color(0x9932CC)
BASE64_COLOR = Color(0x9932CC)
HASH_COLOR = Color(0x8B4513)
REMINDER_COLOR = Color(0x00FF7F)
WEATHER_COLOR = Color(0x87CEEB)
WEATHER_FALLBACK_COLOR = Color(0xFFAA00)
QR_COLOR = Color(0x000000)
POLL_COLOR = Color(0x1E90FF)
TRANSLATE_COLOR = Color(0x4285F4)
ERROR_COLOR = Color(0xFF0000)


# Shared constants
COLOR_NAME_MAP = {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "black": "#000000",
    "white": "#FFFFFF",
    "gray": "#808080",
    "orange": "#FFA500",
    "purple": "#800080",
    "pink": "#FFC0CB",
    "brown": "#A52A2A",
    "gold": "#FFD700",
    "silver": "#C0C0C0",
    "discord": "#5865F2",
    "blurple": "#5865F2",
}

TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
)

BASE64_ACTIONS = {"encode", "decode", "enc", "dec"}
HASH_ALGORITHMS = {"md5": "md5", "sha1": "sha1", "sha256": "sha256"}

REMINDER_MAX_MINUTES = 60 * 24 * 7  # 1 week
REMINDER_MESSAGE_LIMIT = 1024

QR_TEXT_LIMIT = 1000
POLL_MAX_OPTIONS = 4
POLL_NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

TRANSLATE_LANGUAGE_CODES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "pl": "Polish",
    "tr": "Turkish",
    "th": "Thai",
}

