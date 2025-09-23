from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, TypeVar

import hikari
import lightbulb

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from ..core.bot import DiscordBot

T = TypeVar("T")

SUCCESS_COLOR = hikari.Color(0x57F287)
ERROR_COLOR = hikari.Color(0xED4245)

logger = logging.getLogger(__name__)


class BasePlugin:
    def __init__(self, bot: DiscordBot) -> None:
        self.bot = bot
        self.name = self.__class__.__name__.lower().replace("plugin", "")
        self.logger = logging.getLogger(f"plugin.{self.name}")
        self._event_listeners: list[Any] = []
        # Import CommandRegistry here to avoid circular import
        from .commands import CommandRegistry

        self._command_registry: CommandRegistry = CommandRegistry(self)
        self.db = bot.db
        self.events = bot.event_system
        self.permissions = bot.permission_manager
        self.web_panel = getattr(bot, "web_panel_manager", None)
        self.command_client = bot.command_client
        self.gateway = bot.gateway
        self.rest = bot.rest
        self.cache = bot.cache
        self.services = getattr(bot, "services", {})

    async def on_load(self) -> None:
        await self._command_registry.register_commands()
        await self._register_event_listeners()
        await self._register_web_panel()
        self.logger.info(f"Plugin {self.name} loaded successfully")

    async def on_unload(self) -> None:
        await self._command_registry.unregister_commands()
        await self._unregister_event_listeners()
        await self._unregister_web_panel()
        self.logger.info(f"Plugin {self.name} unloaded successfully")

    async def _register_event_listeners(self) -> None:
        # Register event listeners
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "_event_listener"):
                event_name = attr._event_listener
                self.events.add_listener(event_name, attr)
                self._event_listeners.append((event_name, attr))
                self.logger.debug(f"Registered event listener: {attr_name} -> {event_name}")

    async def _unregister_event_listeners(self) -> None:
        # Unregister event listeners
        for event_name, listener in self._event_listeners:
            self.events.remove_listener(event_name, listener)

        self._event_listeners.clear()

    async def _register_web_panel(self) -> None:
        # Register web panel if plugin supports it
        from ..web.mixins import WebPanelMixin

        if isinstance(self, WebPanelMixin):
            if self.web_panel:
                self.web_panel.register_plugin_panel(self.name, self)
            self.logger.debug(f"Registered web panel for plugin: {self.name}")

    async def _unregister_web_panel(self) -> None:
        # Unregister web panel if plugin supports it
        from ..web.mixins import WebPanelMixin

        if isinstance(self, WebPanelMixin):
            if self.web_panel:
                self.web_panel.unregister_plugin_panel(self.name)
            self.logger.debug(f"Unregistered web panel for plugin: {self.name}")

    async def get_setting(self, guild_id: int, key: str, default: Any = None) -> Any:
        # Get plugin-specific setting for a guild
        async with self.db.session() as session:
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
            async with self.db.session() as session:
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
                    plugin_setting = PluginSetting(guild_id=guild_id, plugin_name=self.name, settings={key: value})
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
            async with self.db.session() as session:
                from sqlalchemy import select

                from ..database.models import CommandUsage, Guild, User

                # Ensure user exists in database
                user_result = await session.execute(select(User).where(User.id == ctx.author.id))
                user = user_result.scalar_one_or_none()

                if not user:
                    # Create user if doesn't exist
                    user = User(
                        id=ctx.author.id,
                        username=ctx.author.username,
                        discriminator=getattr(ctx.author, "discriminator", "0000"),
                    )
                    session.add(user)

                # Ensure guild exists in database if guild_id is provided
                if ctx.guild_id:
                    guild_result = await session.execute(select(Guild).where(Guild.id == ctx.guild_id))
                    guild = guild_result.scalar_one_or_none()

                    if not guild:
                        # Create guild if doesn't exist
                        guild_obj = ctx.get_guild()
                        guild = Guild(
                            id=ctx.guild_id,
                            name=guild_obj.name if guild_obj else "Unknown Guild",
                        )
                        session.add(guild)

                # Flush to ensure user/guild are created before adding command usage
                await session.flush()

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

    @asynccontextmanager
    async def db_session(self) -> AsyncIterator[AsyncSession]:
        """Alias for the shared database session context manager."""

        async with self.db.session() as session:
            yield session

    async def with_session(
        self,
        callback: Callable[[AsyncSession], Awaitable[T]],
    ) -> T:
        """Execute a callback within a managed database session."""

        async with self.db_session() as session:
            return await callback(session)

    async def get_guild_prefix(self, guild_id: int) -> str:
        """Shortcut to the shared guild prefix helper."""

        return await self.bot.get_guild_prefix(guild_id)

    async def emit_event(self, event_name: str, *args: Any, suppress_errors: bool = True, **kwargs: Any) -> None:
        """Convenience wrapper for :class:`EventSystem.emit`."""

        try:
            await self.events.emit(event_name, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging
            if suppress_errors:
                self.logger.error("Failed to emit event %s: %s", event_name, exc)
            else:
                raise

    @asynccontextmanager
    async def track_command(self, ctx: lightbulb.Context, command_name: str) -> AsyncIterator[None]:
        """Context manager that records command success or failure automatically."""

        try:
            yield
        except Exception as exc:
            await self.log_command_usage(ctx, command_name, False, str(exc))
            raise
        else:
            await self.log_command_usage(ctx, command_name, True)

    async def respond_success(
        self,
        ctx: lightbulb.Context,
        message: str | None = None,
        *,
        title: str | None = None,
        embed: hikari.Embed | None = None,
        command_name: str | None = None,
        ephemeral: bool = False,
        log: bool = True,
        color: hikari.Color = SUCCESS_COLOR,
        **kwargs: Any,
    ) -> None:
        """Respond with a success-styled embed and optionally log usage."""

        response_embed = embed or self.create_embed(title=title, description=message, color=color)
        await self.smart_respond(ctx, embed=response_embed, ephemeral=ephemeral, **kwargs)
        if log and command_name:
            await self.log_command_usage(ctx, command_name, True)

    async def respond_error(
        self,
        ctx: lightbulb.Context,
        message: str,
        *,
        title: str | None = "❌ Error",
        embed: hikari.Embed | None = None,
        command_name: str | None = None,
        ephemeral: bool = True,
        log: bool = True,
        color: hikari.Color = ERROR_COLOR,
        **kwargs: Any,
    ) -> None:
        """Respond with an error embed and optionally log the failure."""

        response_embed = embed or self.create_embed(title=title, description=message, color=color)
        await self.smart_respond(ctx, embed=response_embed, ephemeral=ephemeral, **kwargs)
        if log and command_name:
            await self.log_command_usage(ctx, command_name, False, message)

    async def fetch_user(self, user_id: int) -> hikari.User:
        """Fetch a user using the shared REST client."""

        return await self.rest.fetch_user(user_id)

    async def fetch_channel(self, channel_id: int) -> hikari.PartialChannel:
        """Fetch a channel using the shared REST client."""

        return await self.rest.fetch_channel(channel_id)

    async def update_voice_state(self, guild_id: int, channel_id: int | None) -> None:
        """Proxy for :meth:`hikari.GatewayBot.update_voice_state`."""

        await self.gateway.update_voice_state(guild_id, channel_id)

    def get_voice_state(self, guild_id: int, user_id: int) -> hikari.VoiceState | None:
        """Retrieve a voice state from the gateway cache."""

        return self.cache.get_voice_state(guild_id, user_id)
