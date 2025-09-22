from __future__ import annotations

"""Static configuration, feature mappings, and validation limits for the admin plugin."""

from hikari import Color

PERMISSION_LIST_LIMIT = 20

SERVER_INFO_COLOR = Color(0x7289DA)
UPTIME_COLOR = Color(0x00FF7F)
SUCCESS_COLOR = Color(0x00FF00)
WARNING_COLOR = Color(0xFFAA00)
ERROR_COLOR = Color(0xFF0000)

SERVER_FEATURE_MAPPING = {
    "COMMUNITY": "Community Server",
    "VERIFIED": "Verified",
    "PARTNERED": "Partnered",
    "ANIMATED_ICON": "Animated Icon",
    "BANNER": "Server Banner",
    "VANITY_URL": "Custom Invite URL",
    "INVITE_SPLASH": "Invite Splash",
    "NEWS": "News Channels",
    "DISCOVERABLE": "Server Discovery",
}

PREFIX_MAX_LENGTH = 5
PREFIX_DISALLOWED_CHARS = {'"', "'", "`", "\n", "\r", "\t"}

AUTOROLE_VALID_ACTIONS = {"add", "remove", "list", "clear"}
