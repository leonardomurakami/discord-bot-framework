from .help import HelpPlugin

PLUGIN_METADATA = {
    "name": "Help",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Comprehensive help system showing commands and usage information",
    "dependencies": [],
    "permissions": [
        "help.commands",
        "help.plugins"
    ],
}


def setup(bot):
    return HelpPlugin(bot)
