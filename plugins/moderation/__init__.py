from .moderation_plugin import ModerationPlugin

PLUGIN_METADATA = {
    "name": "Moderation",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Moderation commands for server management",
    "dependencies": [],
    "permissions": [
        "moderation.kick",
        "moderation.ban",
        "moderation.mute",
        "moderation.warn",
        "moderation.purge",
        "moderation.timeout",
        "moderation.slowmode",
    ],
}


def setup(bot):
    return ModerationPlugin(bot)
