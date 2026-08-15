from __future__ import annotations

"""Static configuration, feature mappings, and validation limits for the admin plugin."""

import hikari  # noqa: E402
from hikari import Color  # noqa: E402

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


# ---------------------------------------------------------------------------
# Shared validation helpers (reused by commands and web routes)
# ---------------------------------------------------------------------------


def validate_prefix(prefix: str) -> tuple[bool, str]:
    """Validate a command prefix.

    Returns ``(is_valid, error_message)``.  When *is_valid* is ``True`` the
    error message is an empty string.
    """
    if len(prefix) > PREFIX_MAX_LENGTH:
        return False, f"Prefix must be {PREFIX_MAX_LENGTH} characters or less."
    if len(prefix.strip()) == 0:
        return False, "Prefix cannot be empty or only whitespace."
    if any(char in prefix for char in PREFIX_DISALLOWED_CHARS):
        return False, "Prefix cannot contain quotes, backticks, or whitespace characters."
    return True, ""


async def check_autorole_hierarchy(guild: hikari.Guild | None, role: hikari.Role, bot_id: int) -> tuple[bool, str]:
    """Check whether the bot can manage *role* based on role hierarchy.

    Returns ``(is_valid, error_message)``.  When *is_valid* is ``True`` the
    error message is an empty string.
    """
    bot_member = guild.get_member(bot_id) if guild else None
    if not bot_member:
        return False, "Cannot verify bot permissions."
    bot_role_ids = bot_member.role_ids or []
    bot_roles = [guild.get_role(rid) for rid in bot_role_ids] if guild else []
    bot_roles = [r for r in bot_roles if r is not None]
    bot_top_role_position = max((r.position for r in bot_roles), default=-1)
    if role.position >= bot_top_role_position and bot_roles:
        return False, "I cannot assign that role because it's higher than or equal to my highest role."
    return True, ""
