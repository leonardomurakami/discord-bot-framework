"""Argument parsers using strategy pattern."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import hikari
from .argument_types import CommandArgument

logger = logging.getLogger(__name__)


class ArgumentParser(ABC):
    """Base class for argument parsers."""
    
    @abstractmethod
    async def parse(self, arg: str, definition: CommandArgument, bot: Any, guild_id: int) -> Any:
        """Parse a string argument according to the definition."""
        pass


class StringArgumentParser(ArgumentParser):
    """Parser for string arguments."""
    
    async def parse(self, arg: str, definition: CommandArgument, bot: Any, guild_id: int) -> Any:
        return arg


class IntegerArgumentParser(ArgumentParser):
    """Parser for integer arguments."""
    
    async def parse(self, arg: str, definition: CommandArgument, bot: Any, guild_id: int) -> Any:
        try:
            return int(arg)
        except ValueError:
            return definition.default


class BooleanArgumentParser(ArgumentParser):
    """Parser for boolean arguments."""
    
    async def parse(self, arg: str, definition: CommandArgument, bot: Any, guild_id: int) -> Any:
        return arg.lower() in ('true', '1', 'yes', 'on', 'y')


class UserArgumentParser(ArgumentParser):
    """Parser for user arguments."""
    
    async def parse(self, arg: str, definition: CommandArgument, bot: Any, guild_id: int) -> Any:
        # Parse user mention or ID
        user_input = arg.strip('<@!>')
        try:
            user_id = int(user_input)
            return await bot.hikari_bot.rest.fetch_user(user_id)
        except (ValueError, hikari.NotFoundError):
            # Try to find by username
            guild = bot.hikari_bot.cache.get_guild(guild_id)
            if guild:
                members = bot.hikari_bot.cache.get_members_view_for_guild(guild_id)
                for member in members.values():
                    if (member.username.lower() == arg.lower() or 
                        member.display_name.lower() == arg.lower()):
                        return member.user
            return definition.default


class ChannelArgumentParser(ArgumentParser):
    """Parser for channel arguments."""
    
    async def parse(self, arg: str, definition: CommandArgument, bot: Any, guild_id: int) -> Any:
        # Parse channel mention or ID
        channel_input = arg.strip('<#>')
        try:
            channel_id = int(channel_input)
            channel = bot.hikari_bot.cache.get_guild_channel(channel_id)
            if not channel:
                # Try fetching from REST API
                channel = await bot.hikari_bot.rest.fetch_channel(channel_id)
            return channel
        except (ValueError, hikari.NotFoundError):
            # Try to find by name
            guild = bot.hikari_bot.cache.get_guild(guild_id)
            if guild:
                channels = bot.hikari_bot.cache.get_guild_channels_view_for_guild(guild_id)
                for channel in channels.values():
                    if hasattr(channel, 'name') and channel.name.lower() == arg.lower():
                        return channel
            return definition.default


class RoleArgumentParser(ArgumentParser):
    """Parser for role arguments."""
    
    async def parse(self, arg: str, definition: CommandArgument, bot: Any, guild_id: int) -> Any:
        # Parse role mention or ID
        role_input = arg.strip('<@&>')
        try:
            role_id = int(role_input)
            role = bot.hikari_bot.cache.get_role(role_id)
            if not role:
                # Try fetching from guild roles
                guild = bot.hikari_bot.cache.get_guild(guild_id)
                if guild:
                    roles = await bot.hikari_bot.rest.fetch_roles(guild_id)
                    for role in roles:
                        if role.id == role_id:
                            return role
            return role
        except (ValueError, hikari.NotFoundError):
            # Try to find by name
            try:
                roles = await bot.hikari_bot.rest.fetch_roles(guild_id)
                for role in roles:
                    if role.name.lower() == arg.lower():
                        return role
            except Exception:
                pass
            return definition.default


class MentionableArgumentParser(ArgumentParser):
    """Parser for mentionable arguments (users or roles)."""
    
    async def parse(self, arg: str, definition: CommandArgument, bot: Any, guild_id: int) -> Any:
        # Try user mention first
        if arg.startswith('<@'):
            user_input = arg.strip('<@!>')
            try:
                user_id = int(user_input)
                return await bot.hikari_bot.rest.fetch_user(user_id)
            except (ValueError, hikari.NotFoundError):
                pass
        
        # Try role mention
        elif arg.startswith('<@&'):
            role_input = arg.strip('<@&>')
            try:
                role_id = int(role_input)
                return bot.hikari_bot.cache.get_role(role_id)
            except (ValueError, hikari.NotFoundError):
                pass
        
        return definition.default


class ArgumentParserFactory:
    """Factory for creating argument parsers."""
    
    _parsers = {
        hikari.OptionType.STRING: StringArgumentParser(),
        hikari.OptionType.INTEGER: IntegerArgumentParser(),
        hikari.OptionType.BOOLEAN: BooleanArgumentParser(),
        hikari.OptionType.USER: UserArgumentParser(),
        hikari.OptionType.CHANNEL: ChannelArgumentParser(),
        hikari.OptionType.ROLE: RoleArgumentParser(),
        hikari.OptionType.MENTIONABLE: MentionableArgumentParser(),
    }
    
    @classmethod
    def get_parser(cls, option_type: hikari.OptionType) -> ArgumentParser:
        """Get the appropriate parser for an option type."""
        return cls._parsers.get(option_type, StringArgumentParser())
    
    @classmethod
    async def parse_arguments(
        cls, 
        args: List[str], 
        command_args: List[CommandArgument], 
        bot: Any, 
        guild_id: int
    ) -> Dict[str, Any]:
        """Parse prefix command arguments based on command definitions."""
        parsed = {}
        
        if not command_args:
            return parsed
        
        # Handle different argument patterns
        for i, arg_def in enumerate(command_args):
            if i < len(args):
                try:
                    # Special handling for last string argument (gets all remaining text)
                    if (arg_def.arg_type == hikari.OptionType.STRING and 
                        i == len(command_args) - 1):
                        parsed[arg_def.name] = " ".join(args[i:])
                    else:
                        parser = cls.get_parser(arg_def.arg_type)
                        parsed[arg_def.name] = await parser.parse(args[i], arg_def, bot, guild_id)
                        
                except Exception as e:
                    logger.warning(f"Error parsing argument {arg_def.name}: {e}")
                    # If parsing fails, use default
                    parsed[arg_def.name] = arg_def.default if not arg_def.required else None
            else:
                # Missing argument
                parsed[arg_def.name] = arg_def.default if not arg_def.required else None
        
        return parsed
