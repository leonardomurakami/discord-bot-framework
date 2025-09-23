import logging
import warnings
from dataclasses import dataclass
from typing import Any

import hikari
import lightbulb
import miru

from config.settings import settings

from ..database import db_manager
from ..permissions import PermissionManager
from .event_system import EventSystem
from .message_handler import MessageCommandHandler
from .plugin_loader import PluginLoader

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BotOverview:
    user: hikari.OwnUser | hikari.User
    guild_count: int
    plugin_count: int
    database_connected: bool


@dataclass(slots=True)
class GuildSummary:
    member_count: int
    channel_count: int
    role_count: int
    emoji_count: int
    text_channels: int
    voice_channels: int
    category_channels: int


class DiscordBot:
    def __init__(self) -> None:
        # Initialize bot components with required intents
        intents = (
            hikari.Intents.ALL_MESSAGES
            | hikari.Intents.GUILD_MEMBERS
            | hikari.Intents.GUILDS
            | hikari.Intents.MESSAGE_CONTENT
            | hikari.Intents.GUILD_VOICE_STATES  # Required for voice/music functionality
        )
        # Create Hikari bot first
        self.hikari_bot = hikari.GatewayBot(token=settings.discord_token, intents=intents)
        # Create lightbulb client
        self._command_client = lightbulb.client_from_app(self.hikari_bot)
        self._bot_attr_warning_emitted = False

        # Initialize miru client and store it as an instance attribute
        self.miru_client = miru.Client(self.hikari_bot)

        # Subscribe client to bot events
        self.hikari_bot.subscribe(hikari.StartingEvent, self._command_client.start)

        # Store reference to our bot instance for permission checks
        import bot.permissions.decorators as perm_decorators

        perm_decorators._bot_instance = self

        # Initialize systems
        self.db = db_manager
        self.event_system = EventSystem()
        self.message_handler = MessageCommandHandler(self)
        self.plugin_loader = PluginLoader(self)
        self.permission_manager = PermissionManager(self.db)

        # Initialize web panel manager
        from ..web import WebPanelManager

        self.web_panel_manager = WebPanelManager(self)

        # Service registry for convenient access
        self.services: dict[str, Any] = {}
        self._register_core_services()

        # Bot state
        self.is_ready = False
        self._startup_tasks: list = []

        # Setup plugin directories
        for directory in settings.plugin_directories:
            self.plugin_loader.add_plugin_directory(directory)

        # Plugin loader ready

        # Setup event listeners
        self._setup_event_listeners()

    def _register_core_services(self) -> None:
        """Populate the core service registry."""

        self.services.update(
            {
                "gateway": self.hikari_bot,
                "command_client": self._command_client,
                "miru": self.miru_client,
                "db": self.db,
                "events": self.event_system,
                "message_handler": self.message_handler,
                "plugin_loader": self.plugin_loader,
                "permissions": self.permission_manager,
                "web_panel": self.web_panel_manager,
            }
        )

    def register_service(self, name: str, service: Any) -> None:
        """Register or override a service in the registry."""

        self.services[name] = service

    def get_service(self, name: str) -> Any:
        """Retrieve a service by name from the registry."""

        return self.services.get(name)

    def _setup_event_listeners(self) -> None:
        @self.hikari_bot.listen(hikari.StartingEvent)
        async def on_starting(event: hikari.StartingEvent) -> None:
            logger.info("Bot is starting...")

        @self.hikari_bot.listen(hikari.StartedEvent)
        async def on_started(event: hikari.StartedEvent) -> None:
            logger.info("Bot has started, initializing systems...")
            await self._initialize_systems()

        @self.hikari_bot.listen(hikari.ShardReadyEvent)
        async def on_ready(event: hikari.ShardReadyEvent) -> None:
            if not self.is_ready:
                logger.info(f"Bot is ready! Logged in as {self.hikari_bot.get_me()}")
                await self.event_system.emit("bot_ready", self)
                self.is_ready = True

        @self.hikari_bot.listen(hikari.StoppingEvent)
        async def on_stopping(event: hikari.StoppingEvent) -> None:
            logger.info("Bot is stopping...")
            await self._cleanup()

        @self.hikari_bot.listen(hikari.GuildAvailableEvent)
        async def on_guild_join(event: hikari.GuildAvailableEvent) -> None:
            await self.event_system.emit("guild_join", event.guild)

        @self.hikari_bot.listen(hikari.GuildUnavailableEvent)
        async def on_guild_leave(event: hikari.GuildUnavailableEvent) -> None:
            await self.event_system.emit("guild_leave", event.guild_id)

        @self.hikari_bot.listen(hikari.MemberCreateEvent)
        async def on_member_join(event: hikari.MemberCreateEvent) -> None:
            await self.event_system.emit("member_join", event.member)

        @self.hikari_bot.listen(hikari.MemberDeleteEvent)
        async def on_member_leave(event: hikari.MemberDeleteEvent) -> None:
            await self.event_system.emit("member_leave", event.user, event.guild_id)

        @self.hikari_bot.listen(hikari.GuildMessageCreateEvent)
        async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
            # Debug logging for all messages
            logger.debug(
                f"Message received: '{event.content}' from {event.author.username} "
                f"in #{event.get_channel().name if event.get_channel() else 'unknown'}"
            )

            # Log if it's a potential command
            potential_prefix = await self.get_guild_prefix(event.guild_id) if event.guild_id else settings.bot_prefix
            if event.content and (event.content.startswith("/") or event.content.startswith(potential_prefix)):
                logger.info(f"Potential command detected: '{event.content}' from {event.author.username}")

            # Handle prefix commands via our custom handler
            handled = await self.message_handler.handle_message(event)
            if not handled:
                await self.event_system.emit("message_create", event)

    @property
    def command_client(self) -> lightbulb.LightbulbApp:
        """Return the Lightbulb command client."""

        return self._command_client

    @property
    def bot(self) -> lightbulb.LightbulbApp:
        """Deprecated alias for :pyattr:`command_client`."""

        if not self._bot_attr_warning_emitted:
            warnings.warn(
                "DiscordBot.bot is deprecated; use DiscordBot.command_client instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._bot_attr_warning_emitted = True
        return self._command_client

    @property
    def gateway(self) -> hikari.GatewayBot:
        return self.hikari_bot

    @property
    def rest(self) -> hikari.api.RESTClient:
        return self.hikari_bot.rest

    @property
    def cache(self) -> hikari.api.CacheView:
        return self.hikari_bot.cache

    async def _initialize_systems(self) -> None:
        try:
            # Initialize database
            await self.db.create_tables()
            logger.info("Database initialized")

            # Initialize permissions (without plugin discovery first)
            self.permission_manager.set_bot(self)
            await self.permission_manager.initialize()
            logger.info("Permission system initialized")

            # Load plugins
            await self._load_plugins()
            logger.info("Plugins loaded")

            # Refresh permissions to discover plugin-defined permissions
            await self.permission_manager.refresh_permissions()
            logger.info("Permissions discovered from plugins")

            # Start web panel
            await self.web_panel_manager.start()
            logger.info("Web panel started")

            # Run startup tasks
            for task in self._startup_tasks:
                await task()

            logger.info("All systems initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize systems: {e}")
            raise

    async def _load_plugins(self) -> None:
        try:
            enabled_plugins = settings.enabled_plugins
            discovered = self.plugin_loader.discover_plugins()

            # Load only enabled plugins that were discovered
            plugins_to_load = [p for p in enabled_plugins if p in discovered]

            if plugins_to_load:
                logger.info(f"Loading plugins: {plugins_to_load}")
                await self.plugin_loader.load_all_plugins(plugins_to_load)
            else:
                logger.warning("No valid plugins found to load")

        except Exception as e:
            logger.error(f"Error loading plugins: {e}")

    async def _cleanup(self) -> None:
        try:
            # Emit cleanup event
            await self.event_system.emit("bot_stopping", self)

            # Stop web panel
            await self.web_panel_manager.stop()

            # Unload all plugins
            for plugin_name in list(self.plugin_loader.plugins.keys()):
                await self.plugin_loader.unload_plugin(plugin_name)

            # Close database
            await self.db.close()

            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def add_startup_task(self, task) -> None:
        self._startup_tasks.append(task)

    async def get_bot_overview(self) -> BotOverview:
        """Return a snapshot of the bot's runtime state."""

        guilds_view = self.cache.get_guilds_view() if self.cache else {}
        plugin_count = len(self.plugin_loader.get_loaded_plugins())
        db_healthy = await self.db.health_check()
        return BotOverview(self.hikari_bot.get_me(), len(guilds_view), plugin_count, db_healthy)

    def summarise_guild(self, guild: hikari.Guild) -> GuildSummary:
        """Aggregate commonly requested guild statistics."""

        channels = guild.get_channels()
        text_channels = len([c for c in channels.values() if c.type == hikari.ChannelType.GUILD_TEXT])
        voice_channels = len([c for c in channels.values() if c.type == hikari.ChannelType.GUILD_VOICE])
        category_channels = len([c for c in channels.values() if c.type == hikari.ChannelType.GUILD_CATEGORY])

        return GuildSummary(
            member_count=guild.member_count or 0,
            channel_count=len(channels),
            role_count=len(guild.get_roles()),
            emoji_count=len(guild.get_emojis()),
            text_channels=text_channels,
            voice_channels=voice_channels,
            category_channels=category_channels,
        )

    async def get_guild_prefix(self, guild_id: int) -> str:
        """Get the prefix for a specific guild, falling back to default if not found."""
        try:
            async with self.db.session() as session:
                from sqlalchemy import select

                from bot.database.models import Guild

                result = await session.execute(select(Guild).where(Guild.id == guild_id))
                guild = result.scalar_one_or_none()

                if guild and guild.prefix:
                    return guild.prefix

        except Exception as e:
            logger.error(f"Error getting guild prefix for {guild_id}: {e}")

        # Return default prefix if no guild found or error occurred
        return settings.bot_prefix

    def run(self) -> None:
        try:
            logger.info("Starting Discord bot...")
            self.hikari_bot.run()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise
