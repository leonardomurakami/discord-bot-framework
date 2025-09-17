from .music import MusicPlugin

PLUGIN_METADATA = {
    "name": "Music",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Music player with queue management, repeat modes, and auto-disconnect features",
    "permissions": ["music.play", "music.manage", "music.settings"],
}

__all__ = ["MusicPlugin"]