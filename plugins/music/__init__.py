from .music import MusicPlugin

PLUGIN_METADATA = {
    "name": "Music",
    "version": "3.0.0",
    "author": "Bot Framework",
    "description": "Feature-complete music bot with interactive controls, search selection, playlist support, queue management, and auto-disconnect",
    "permissions": ["music.play", "music.manage", "music.settings"],
}

__all__ = ["MusicPlugin"]