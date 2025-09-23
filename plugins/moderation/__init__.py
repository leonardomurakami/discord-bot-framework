from .plugin import ModerationPlugin

PLUGIN_METADATA = {
    "name": "Moderation",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Moderation commands for server management",
    "dependencies": [],
    "permissions": [
        "moderation.manage",
        "moderation.members.kick",
        "moderation.members.ban",
        "moderation.members.mute",
        "moderation.members.warn",
        "moderation.members.timeout",
        "moderation.members.nickname",
        "moderation.channels.purge",
        "moderation.channels.slowmode",
    ],
}


def setup(bot):
    return ModerationPlugin(bot)
