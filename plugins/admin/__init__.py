from .admin import AdminPlugin

PLUGIN_METADATA = {
    "name": "Admin",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Administrative commands for bot management",
    "dependencies": [],
    "permissions": [
        "admin.config",
        "admin.plugins",
        "admin.permissions"
    ],
}


def setup(bot):
    return AdminPlugin(bot)