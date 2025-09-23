from .plugin import FunPlugin

PLUGIN_METADATA = {
    "name": "Fun",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Fun commands and games for entertainment",
    "dependencies": [],
    "permissions": ["basic.fun.games.play", "basic.fun.images.view"],
}


def setup(bot):
    return FunPlugin(bot)
