from .plugin import MusicPlugin

PLUGIN_METADATA = {
    "name": "Music",
    "version": "4.0.0",
    "author": "Bot Framework",
    "description": (
        "Advanced music bot with persistent queues, interactive controls, search selection, "
        "playlist support, queue management, auto-disconnect, and music history tracking"
    ),
    "permissions": [
        "music.manage",
        "basic.music.playback.control",
        "basic.music.queue.view",
        "basic.music.queue.control",
        "basic.music.voice.control",
        "basic.music.search.use",
        "music.queue.manage",
        "music.voice.manage",
        "music.settings.manage",
    ],
}

__all__ = ["MusicPlugin"]
