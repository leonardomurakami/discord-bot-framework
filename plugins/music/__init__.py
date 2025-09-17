from .music_plugin import MusicPlugin

PLUGIN_METADATA = {
    "name": "Music",
    "version": "4.0.0",
    "author": "Bot Framework",
    "description": "Advanced music bot with persistent queues, interactive controls, search selection, playlist support, queue management, auto-disconnect, and music history tracking",
    "permissions": ["music.play", "music.manage", "music.settings"],
}

__all__ = ["MusicPlugin"]