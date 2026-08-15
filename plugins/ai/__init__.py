from .plugin import AIPlugin

PLUGIN_METADATA = {
    "name": "AI",
    "version": "1.0.0",
    "author": "Discord Bot Framework",
    "description": "Chat with an AI model via the acpbox OpenAI-compatible endpoint",
    "dependencies": [],
    "permissions": ["basic.ai.chat", "basic.ai.clear"],
}


def setup(bot):
    return AIPlugin(bot)


__all__ = ["AIPlugin", "PLUGIN_METADATA"]
