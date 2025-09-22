import logging

logger = logging.getLogger(__name__)


class CommandInfoManager:
    """Manages command and plugin information retrieval."""

    def __init__(self, help_plugin):
        self.help_plugin = help_plugin
        self.bot = help_plugin.bot

    def get_command_info(self, command_name: str) -> dict | None:
        """Get detailed information for a specific command."""
        # Get prefix safely
        prefix = "!"  # Default prefix
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                prefix = getattr(self.bot.message_handler, "prefix", "!")
        except (AttributeError, TypeError):
            pass

        # Get commands safely
        commands = {}
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                commands = self.bot.message_handler.commands
        except (AttributeError, TypeError):
            pass

        # First check direct command match
        for cmd in commands.values():
            if hasattr(cmd, "name") and cmd.name == command_name:
                return {
                    "name": cmd.name,
                    "description": getattr(cmd, "description", None),
                    "aliases": getattr(cmd, "aliases", []),
                    "permission_node": getattr(cmd, "permission_node", None),
                    "usage": f"{prefix}{cmd.name}",
                    "plugin_name": getattr(cmd, "plugin_name", None),
                }

        # Then check aliases
        for cmd in commands.values():
            if hasattr(cmd, "aliases") and cmd.aliases and command_name in cmd.aliases:
                return {
                    "name": getattr(cmd, "name", "Unknown"),
                    "description": getattr(cmd, "description", None),
                    "aliases": getattr(cmd, "aliases", []),
                    "permission_node": getattr(cmd, "permission_node", None),
                    "usage": f"{prefix}{getattr(cmd, 'name', 'unknown')}",
                    "plugin_name": getattr(cmd, "plugin_name", None),
                }

        return None

    def get_plugin_overview(self, plugin_name: str, plugin_obj) -> str:
        """Get a brief overview of a plugin for listing purposes."""
        try:
            if hasattr(plugin_obj, "plugin_info"):
                info = plugin_obj.plugin_info
                name = info.get("name", plugin_name.title())
                version = info.get("version", "Unknown")
                author = info.get("author", "Unknown")
                commands = info.get("commands", [])
                cmd_count = len(commands) if commands else 0

                return f"**{name}** v{version} by {author} ({cmd_count} commands)"
            else:
                return f"**{plugin_name.title()}** - No metadata available"
        except Exception:
            return f"**{plugin_name.title()}** - Information unavailable"

    def format_command_list(self, commands: list[dict]) -> list[str]:
        """Format a list of commands into strings that fit Discord embed field limits."""
        if not commands:
            return ["No commands available."]

        formatted_pages = []
        current_page = ""

        for cmd in commands:
            cmd_name = cmd.get("name", "Unknown")
            cmd_desc = cmd.get("description", "No description")

            cmd_line = f"**{cmd_name}** - {cmd_desc}\n"

            # Check if adding this command would exceed the 1024 character limit
            if len(current_page + cmd_line) > 1000:  # Leave some buffer
                if current_page:
                    formatted_pages.append(current_page.strip())
                current_page = cmd_line
            else:
                current_page += cmd_line

        # Add the last page if it has content
        if current_page.strip():
            formatted_pages.append(current_page.strip())

        return formatted_pages if formatted_pages else ["No commands available."]

    async def get_prefix(self, guild_id: int = None) -> str:
        """Get the guild-specific command prefix safely."""
        try:
            if guild_id and hasattr(self.bot, "get_guild_prefix"):
                return await self.bot.get_guild_prefix(guild_id)
        except (AttributeError, TypeError):
            pass

        # Fallback to default prefix
        try:
            from config.settings import settings

            return settings.bot_prefix
        except (AttributeError, ImportError):
            pass

        return "!"

    def get_bot_statistics(self) -> dict:
        """Get bot statistics like plugin count and command count."""
        stats = {"plugin_count": 0, "unique_commands": 0, "plugin_categories": []}

        # Get plugin count
        try:
            if self.bot.plugin_loader:
                stats["plugin_count"] = len(self.bot.plugin_loader.get_loaded_plugins())
        except (AttributeError, TypeError):
            pass

        # Count unique commands (excluding aliases)
        seen_commands = set()
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                for cmd_name, cmd in self.bot.message_handler.commands.items():
                    if cmd.name == cmd_name and cmd.name not in seen_commands:
                        stats["unique_commands"] += 1
                        seen_commands.add(cmd.name)
        except (AttributeError, TypeError):
            pass

        # Get plugin categories
        try:
            if self.bot.plugin_loader:
                plugins = self.bot.plugin_loader.get_loaded_plugins()
                for plugin_name in plugins:
                    try:
                        plugin_info = self.bot.plugin_loader.get_plugin_info(plugin_name)
                        if plugin_info:
                            stats["plugin_categories"].append(plugin_info.name)
                    except (AttributeError, TypeError):
                        continue
        except (AttributeError, TypeError):
            pass

        return stats

    async def get_essential_commands(self, guild_id: int = None) -> list[str]:
        """Get a list of essential commands for the help overview."""
        essential_commands = []
        command_suggestions = [
            ("ping", "🏓", "Test bot responsiveness"),
            ("help", "❓", "Show this help menu"),
            ("roll", "🎲", "Roll dice for games"),
            ("info", "ℹ️", "Bot information"),
            ("bot-info", "ℹ️", "Bot information"),
            ("commands", "📋", "List all commands"),
            ("plugins", "🔌", "Show loaded plugins"),
        ]

        prefix = await self.get_prefix(guild_id)

        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                for cmd_name, emoji, desc in command_suggestions:
                    if cmd_name in self.bot.message_handler.commands:
                        essential_commands.append(f"{emoji} `{prefix}{cmd_name}` - {desc}")
        except (AttributeError, TypeError):
            pass

        return essential_commands
