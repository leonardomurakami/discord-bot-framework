from __future__ import annotations

"""Static configuration values for the moderation plugin."""

from hikari import Color


ERROR_COLOR = Color(0xFF0000)
SUCCESS_COLOR = Color(0x00FF00)
WARNING_COLOR = Color(0xFFAA00)
NOTICE_COLOR = Color(0x7289DA)
BAN_DM_COLOR = Color(0xFF0000)
KICK_DM_COLOR = Color(0xFF6600)
LOCK_COLOR = Color(0xFF0000)
UNLOCK_COLOR = Color(0x00FF00)
SLOWMODE_ENABLE_COLOR = Color(0xFFAA00)
SLOWMODE_DISABLE_COLOR = Color(0x00FF00)
WARN_DM_COLOR = Color(0xFFAA00)

PURGE_MIN = 1
PURGE_MAX = 100
SLOWMODE_MAX_SECONDS = 21_600  # 6 hours

WARN_DISPLAY_LIMIT = 5
NOTE_DISPLAY_LIMIT = 5

LOCKDOWN_ACTIONS = {"lock", "unlock"}
MODNOTE_ACTIONS = {"add", "view", "clear"}

