from .plugin import HelpPlugin

PLUGIN_METADATA = {
    "name": "Help",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Comprehensive help system showing commands and usage information",
    "dependencies": [],
    "permissions": ["basic.help.commands.view", "basic.help.plugins.view"],
}


def setup(bot):
    return HelpPlugin(bot)
