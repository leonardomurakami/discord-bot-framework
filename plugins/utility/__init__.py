from .utility_plugin import UtilityPlugin

PLUGIN_METADATA = {
    "name": "Utility",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Useful utility commands for various tasks including user info, timestamps, color tools, and text conversion",
    "permissions": ["utility.tools", "utility.info", "utility.convert"],
}

__all__ = ["UtilityPlugin"]
