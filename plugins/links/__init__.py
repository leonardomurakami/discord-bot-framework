from .links_plugin import LinksPlugin

PLUGIN_METADATA = {
    "name": "Links",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Easy access to important links and URLs",
    "dependencies": [],
    "permissions": ["links.view", "links.manage"],
}


def setup(bot):
    return LinksPlugin(bot)