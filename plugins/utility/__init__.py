from .plugin import UtilityPlugin

PLUGIN_METADATA = {
    "name": "Utility",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Useful utility commands for various tasks including user info, timestamps, color tools, and text conversion",
    "permissions": [
        "basic.utility.tools.use",
        "basic.utility.info.view",
        "basic.utility.convert.use",
    ],
}

__all__ = ["UtilityPlugin"]
