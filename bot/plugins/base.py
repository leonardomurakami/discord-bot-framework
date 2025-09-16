import logging
from abc import ABC
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class BasePlugin(ABC):
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.name = self.__class__.__name__.lower().replace("plugin", "")
        self.logger = logging.getLogger(f"plugin.{self.name}")
        self._event_listeners: list[Any] = []
        # Import CommandRegistry here to avoid circular import
        from .commands import CommandRegistry

        self._command_registry: CommandRegistry = CommandRegistry(self)

    async def on_load(self) -> None:
        await self._command_registry.register_commands()
        await self._register_event_listeners()
        self.logger.info(f"Plugin {self.name} loaded successfully")

    async def on_unload(self) -> None:
        await self._command_registry.unregister_commands()
        await self._unregister_event_listeners()
        self.logger.info(f"Plugin {self.name} unloaded successfully")

    async def _register_event_listeners(self) -> None:
        # Register event listeners
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_event_listener"):
                event_name = attr._event_listener
                self.bot.event_system.add_listener(event_name, attr)
                self._event_listeners.append((event_name, attr))
                self.logger.debug(
                    f"Registered event listener: {attr_name} -> {event_name}"
                )

    async def _unregister_event_listeners(self) -> None:
        # Unregister event listeners
        for event_name, listener in self._event_listeners:
            self.bot.event_system.remove_listener(event_name, listener)

        self._event_listeners.clear()

    async def get_setting(self, guild_id: int, key: str, default: Any = None) -> Any:
        # Get plugin-specific setting for a guild
        async with self.bot.db.session() as session:
            from sqlalchemy import select

            from ..database.models import PluginSetting

            result = await session.execute(
                select(PluginSetting).where(
                    PluginSetting.guild_id == guild_id,
                    PluginSetting.plugin_name == self.name,
                )
            )
            plugin_setting = result.scalar_one_or_none()

            if plugin_setting and key in plugin_setting.settings:
                return plugin_setting.settings[key]

            return default

    async def set_setting(self, guild_id: int, key: str, value: Any) -> bool:
        # Set plugin-specific setting for a guild
        try:
            async with self.bot.db.session() as session:
                from sqlalchemy import select

                from ..database.models import PluginSetting

                result = await session.execute(
                    select(PluginSetting).where(
                        PluginSetting.guild_id == guild_id,
                        PluginSetting.plugin_name == self.name,
                    )
                )
                plugin_setting = result.scalar_one_or_none()

                if plugin_setting:
                    plugin_setting.settings[key] = value
                else:
                    plugin_setting = PluginSetting(
                        guild_id=guild_id, plugin_name=self.name, settings={key: value}
                    )
                    session.add(plugin_setting)

                await session.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error setting plugin setting: {e}")
            return False

    async def is_enabled_in_guild(self, guild_id: int) -> bool:
        # Check if plugin is enabled in a specific guild
        enabled = await self.get_setting(guild_id, "enabled", True)
        return bool(enabled)

    async def enable_in_guild(self, guild_id: int) -> bool:
        # Enable plugin in a specific guild
        return await self.set_setting(guild_id, "enabled", True)

    async def disable_in_guild(self, guild_id: int) -> bool:
        # Disable plugin in a specific guild
        return await self.set_setting(guild_id, "enabled", False)

    # Utility methods for plugins
    def create_embed(
        self,
        title: str | None = None,
        description: str | None = None,
        color: hikari.Color = hikari.Color(0x7289DA),
    ) -> hikari.Embed:
        embed = hikari.Embed(title=title, description=description, color=color)
        return embed

    async def smart_respond(
        self,
        ctx: lightbulb.Context,
        content: str = None,
        *,
        embed: hikari.Embed = None,
        ephemeral: bool = False,
        **kwargs,
    ) -> None:
        """Context-aware respond that handles flags properly for both slash and prefix commands."""
        try:
            # For slash commands (InteractionContext), we can use flags
            if hasattr(ctx, "interaction") and ephemeral:
                kwargs["flags"] = hikari.MessageFlag.EPHEMERAL
            # For prefix commands, we ignore the ephemeral flag since it's not supported

            if content:
                kwargs["content"] = content
            if embed:
                kwargs["embed"] = embed

            await ctx.respond(**kwargs)
        except Exception:
            # Fallback: try without flags if the first attempt fails
            kwargs.pop("flags", None)
            if content:
                kwargs["content"] = content
            if embed:
                kwargs["embed"] = embed
            await ctx.respond(**kwargs)

    async def log_command_usage(
        self,
        ctx: lightbulb.Context,
        command_name: str,
        success: bool,
        error_message: str | None = None,
        execution_time: float | None = None,
    ) -> None:
        try:
            async with self.bot.db.session() as session:
                from ..database.models import CommandUsage

                usage = CommandUsage(
                    guild_id=ctx.guild_id or 0,
                    user_id=ctx.author.id,
                    command_name=command_name,
                    plugin_name=self.name,
                    success=success,
                    error_message=error_message,
                    execution_time=execution_time,
                )
                session.add(usage)
                await session.commit()

        except Exception as e:
            self.logger.error(f"Error logging command usage: {e}")
