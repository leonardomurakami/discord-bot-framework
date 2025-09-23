from .plugin import AdminPlugin

PLUGIN_METADATA = {
    "name": "Admin",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Administrative commands for bot management",
    "dependencies": [],
    "permissions": [
        "admin.manage",
        "admin.permissions.manage",
        "admin.config.manage",
        "admin.plugins.manage",
        "basic.admin.info.view",
        "basic.admin.status.view",
    ],
}


def setup(bot):
    return AdminPlugin(bot)
