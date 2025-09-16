import logging
import re
from typing import Dict, List, Any, Optional
import hikari
from config.settings import settings

logger = logging.getLogger(__name__)


class PrefixCommand:
    def __init__(
        self,
        name: str,
        callback: Any,
        description: str = "",
        aliases: Optional[List[str]] = None,
        permission_node: Optional[str] = None,
        plugin_name: Optional[str] = None,
        arguments: Optional[List[Any]] = None
    ):
        self.name = name
        self.callback = callback
        self.description = description
        self.aliases = aliases or []
        self.permission_node = permission_node
        self.plugin_name = plugin_name
        self.arguments = arguments or []


class MessageCommandHandler:
    def __init__(self, bot: Any):
        self.bot = bot
        self.commands: Dict[str, PrefixCommand] = {}
        self.prefix = settings.bot_prefix

    def add_command(self, command: PrefixCommand) -> None:
        self.commands[command.name] = command

        # Add aliases
        for alias in command.aliases:
            self.commands[alias] = command

        logger.debug(f"Added prefix command: {command.name} (aliases: {command.aliases})")

    def remove_command(self, name: str) -> None:
        if name in self.commands:
            command = self.commands[name]

            # Remove main command and aliases
            self.commands.pop(command.name, None)
            for alias in command.aliases:
                self.commands.pop(alias, None)

            logger.debug(f"Removed prefix command: {name}")

    async def handle_message(self, event: hikari.GuildMessageCreateEvent) -> bool:
        # Ignore bot messages
        if event.author.is_bot:
            return False

        # Check if message starts with prefix
        if not event.content or not event.content.startswith(self.prefix):
            return False

        # Parse command and arguments
        content = event.content[len(self.prefix):].strip()
        if not content:
            return False

        parts = content.split()
        command_name = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Find command
        if command_name not in self.commands:
            return False

        command = self.commands[command_name]

        logger.info(f"Prefix command called: {self.prefix}{command_name} by {event.author.username}")

        try:
            # Create a context-like object for prefix commands
            ctx = PrefixContext(event, self.bot, args)

            # Check permissions if required
            if command.permission_node and hasattr(self.bot, 'permission_manager'):
                member = event.member
                if member:
                    has_permission = await self.bot.permission_manager.has_permission(
                        event.guild_id, member, command.permission_node
                    )
                    if not has_permission:
                        await ctx.respond(f"❌ You don't have permission to use `{command.permission_node}`")
                        return True

            # Execute command
            await command.callback(ctx)
            return True

        except Exception as e:
            logger.error(f"Error executing prefix command {command_name}: {e}")
            try:
                await ctx.respond(f"❌ Command failed: {str(e)}")
            except:
                pass
            return True


class PrefixContext:
    def __init__(self, event: hikari.GuildMessageCreateEvent, bot: Any, args: List[str]):
        self.event = event
        self.bot = bot
        self.args = args

        # Mirror Arc context properties
        self.author = event.author
        self.member = event.member
        self.guild_id = event.guild_id
        self.channel_id = event.channel_id

    def get_guild(self) -> Optional[hikari.Guild]:
        if self.guild_id:
            return self.bot.hikari_bot.cache.get_guild(self.guild_id)
        return None

    def get_channel(self) -> Optional[hikari.GuildChannel]:
        return self.event.get_channel()

    async def respond(self, content: str = None, *, embed: hikari.Embed = None, components=None) -> None:
        await self.bot.hikari_bot.rest.create_message(
            self.channel_id,
            content=content,
            embed=embed,
            components=components
        )