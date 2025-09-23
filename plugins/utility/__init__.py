from .plugin import UtilityPlugin

PLUGIN_METADATA = {
    "name": "Utility",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Useful utility commands for various tasks including user info, timestamps, color tools, and text conversion",
    "permissions": ["basic.tools", "basic.info", "basic.convert"],
}

__all__ = ["UtilityPlugin"]
