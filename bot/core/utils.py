"""Utility functions for the Discord bot framework."""

import hikari
import lightbulb


def get_bot_user_id(ctx: lightbulb.Context) -> int:
    """
    Get the bot's user ID, handling both lightbulb.Context and PrefixContext.

    Args:
        ctx: The command context (lightbulb.Context or PrefixContext)

    Returns:
        The bot's user ID
    """
    if hasattr(ctx, "client"):
        # lightbulb.Context
        return ctx.client.get_me().id
    else:
        # PrefixContext
        return ctx.bot.hikari_bot.get_me().id


def calculate_member_permissions(
    member: hikari.Member, guild: hikari.Guild, channel: hikari.GuildChannel | None = None
) -> hikari.Permissions:
    """
    Calculate the effective permissions for a member in a guild or channel.

    Args:
        member: The guild member to calculate permissions for
        guild: The guild the member belongs to
        channel: Optional channel to include channel overwrites

    Returns:
        The calculated permissions for the member
    """
    # Start with @everyone permissions
    everyone_role = guild.get_role(guild.id)  # @everyone role has same ID as guild
    permissions = everyone_role.permissions if everyone_role else hikari.Permissions.NONE

    # Add permissions from all member roles
    for role_id in member.role_ids:
        role = guild.get_role(role_id)
        if role:
            permissions |= role.permissions

    # If member has administrator permission, return all permissions
    if permissions & hikari.Permissions.ADMINISTRATOR:
        return ~hikari.Permissions.NONE  # All permissions set

    # Apply channel overwrites if channel is provided
    if channel and hasattr(channel, "permission_overwrites"):
        # Apply @everyone overwrites first
        everyone_overwrite = channel.permission_overwrites.get(guild.id)
        if everyone_overwrite:
            permissions &= ~everyone_overwrite.deny
            permissions |= everyone_overwrite.allow

        # Apply role overwrites
        for role_id in member.role_ids:
            role_overwrite = channel.permission_overwrites.get(role_id)
            if role_overwrite:
                permissions &= ~role_overwrite.deny
                permissions |= role_overwrite.allow

        # Apply member-specific overwrites (highest priority)
        member_overwrite = channel.permission_overwrites.get(member.id)
        if member_overwrite:
            permissions &= ~member_overwrite.deny
            permissions |= member_overwrite.allow

    return permissions


def has_permissions(
    member: hikari.Member, guild: hikari.Guild, required_permissions: hikari.Permissions, channel: hikari.GuildChannel | None = None
) -> bool:
    """
    Check if a member has the required permissions in a guild or channel.

    Args:
        member: The guild member to check permissions for
        guild: The guild the member belongs to
        required_permissions: The permissions to check for
        channel: Optional channel to include channel overwrites

    Returns:
        True if the member has all required permissions, False otherwise
    """
    member_permissions = calculate_member_permissions(member, guild, channel)
    return (member_permissions & required_permissions) == required_permissions


def format_permissions(permissions: hikari.Permissions) -> list[str]:
    """
    Format permissions into a human-readable list of permission names.

    Args:
        permissions: The permissions to format

    Returns:
        A list of human-readable permission names
    """
    permission_names = []

    # Map of permission flags to human-readable names
    permission_map = {
        hikari.Permissions.CREATE_INSTANT_INVITE: "Create Instant Invite",
        hikari.Permissions.KICK_MEMBERS: "Kick Members",
        hikari.Permissions.BAN_MEMBERS: "Ban Members",
        hikari.Permissions.ADMINISTRATOR: "Administrator",
        hikari.Permissions.MANAGE_CHANNELS: "Manage Channels",
        hikari.Permissions.MANAGE_GUILD: "Manage Server",
        hikari.Permissions.ADD_REACTIONS: "Add Reactions",
        hikari.Permissions.VIEW_AUDIT_LOG: "View Audit Log",
        hikari.Permissions.PRIORITY_SPEAKER: "Priority Speaker",
        hikari.Permissions.STREAM: "Video",
        hikari.Permissions.VIEW_CHANNEL: "View Channels",
        hikari.Permissions.SEND_MESSAGES: "Send Messages",
        hikari.Permissions.SEND_TTS_MESSAGES: "Send TTS Messages",
        hikari.Permissions.MANAGE_MESSAGES: "Manage Messages",
        hikari.Permissions.EMBED_LINKS: "Embed Links",
        hikari.Permissions.ATTACH_FILES: "Attach Files",
        hikari.Permissions.READ_MESSAGE_HISTORY: "Read Message History",
        hikari.Permissions.MENTION_ROLES: "Mention @everyone, @here, and All Roles",
        hikari.Permissions.USE_EXTERNAL_EMOJIS: "Use External Emojis",
        hikari.Permissions.VIEW_GUILD_INSIGHTS: "View Server Insights",
        hikari.Permissions.CONNECT: "Connect",
        hikari.Permissions.SPEAK: "Speak",
        hikari.Permissions.MUTE_MEMBERS: "Mute Members",
        hikari.Permissions.DEAFEN_MEMBERS: "Deafen Members",
        hikari.Permissions.MOVE_MEMBERS: "Move Members",
        hikari.Permissions.USE_VOICE_ACTIVITY: "Use Voice Activity",
        hikari.Permissions.CHANGE_NICKNAME: "Change Nickname",
        hikari.Permissions.MANAGE_NICKNAMES: "Manage Nicknames",
        hikari.Permissions.MANAGE_ROLES: "Manage Roles",
        hikari.Permissions.MANAGE_WEBHOOKS: "Manage Webhooks",
        hikari.Permissions.MANAGE_EMOJIS_AND_STICKERS: "Manage Emojis and Stickers",
        hikari.Permissions.USE_SLASH_COMMANDS: "Use Slash Commands",
        hikari.Permissions.REQUEST_TO_SPEAK: "Request to Speak",
        hikari.Permissions.MANAGE_EVENTS: "Manage Events",
        hikari.Permissions.MANAGE_THREADS: "Manage Threads",
        hikari.Permissions.CREATE_PUBLIC_THREADS: "Create Public Threads",
        hikari.Permissions.CREATE_PRIVATE_THREADS: "Create Private Threads",
        hikari.Permissions.USE_EXTERNAL_STICKERS: "Use External Stickers",
        hikari.Permissions.SEND_MESSAGES_IN_THREADS: "Send Messages in Threads",
        hikari.Permissions.USE_EMBEDDED_ACTIVITIES: "Use Activities",
        hikari.Permissions.MODERATE_MEMBERS: "Timeout Members",
    }

    for permission_flag, permission_name in permission_map.items():
        if permissions & permission_flag:
            permission_names.append(permission_name)

    return permission_names
