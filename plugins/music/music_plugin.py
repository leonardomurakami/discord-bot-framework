import asyncio
import logging
from typing import Any

import hikari

import lavalink
from bot.plugins.base import BasePlugin
from bot.web.mixins import WebPanelMixin
from config.settings import settings

from .commands.history import setup_history_commands
from .commands.nowplaying import setup_nowplaying_commands
from .commands.playback import setup_playback_commands
from .commands.queue import setup_queue_commands
from .commands.search import setup_search_commands
from .commands.settings import setup_settings_commands
from .commands.voice import setup_voice_commands
from .events import MusicEventHandler
from .utils import add_to_history, check_voice_channel_empty, restore_all_queues, save_queue_to_db

logger = logging.getLogger(__name__)


class MusicPlugin(BasePlugin, WebPanelMixin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self.lavalink_client: lavalink.Client | None = None
        self.repeat_modes: dict[int, int] = {}
        self.disconnect_timers: dict[int, Any] = {}
        self._restoring_queues: set[int] = set()

    async def on_load(self) -> None:
        # Register all commands BEFORE calling super().on_load()
        self._register_commands()

        await super().on_load()

        self.lavalink_client = lavalink.Client(self.bot.hikari_bot.get_me().id)
        self.lavalink_client.add_node(
            host=settings.lavalink_host,
            port=settings.lavalink_port,
            password=settings.lavalink_password,
            region="us",
            name="default-node",
        )

        self.lavalink_client.add_event_hooks(MusicEventHandler(self))

        @self.bot.hikari_bot.listen(hikari.VoiceServerUpdateEvent)
        async def voice_server_update(event: hikari.VoiceServerUpdateEvent) -> None:
            lavalink_data = {
                "t": "VOICE_SERVER_UPDATE",
                "d": {
                    "guild_id": event.guild_id,
                    "endpoint": event.endpoint[6:],
                    "token": event.token,
                },
            }
            await self.lavalink_client.voice_update_handler(lavalink_data)

        @self.bot.hikari_bot.listen(hikari.VoiceStateUpdateEvent)
        async def voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:
            lavalink_data = {
                "t": "VOICE_STATE_UPDATE",
                "d": {
                    "guild_id": event.state.guild_id,
                    "user_id": event.state.user_id,
                    "channel_id": event.state.channel_id,
                    "session_id": event.state.session_id,
                },
            }
            await self.lavalink_client.voice_update_handler(lavalink_data)

            if event.state.guild_id and event.state.member is not None and not event.state.member.is_bot:
                player = self.lavalink_client.player_manager.get(event.state.guild_id)
                if player and player.is_connected and player.channel_id:
                    if (event.old_state and event.old_state.channel_id == player.channel_id) or (
                        event.state.channel_id == player.channel_id
                    ):
                        await check_voice_channel_empty(self, event.state.guild_id, player.channel_id)

        logger.info("Music plugin loaded with Lavalink.py")

        asyncio.create_task(restore_all_queues(self))

    async def on_unload(self) -> None:
        for task in self.disconnect_timers.values():
            if not task.done():
                task.cancel()
        self.disconnect_timers.clear()

        if self.lavalink_client:
            await self.lavalink_client.destroy()
        await super().on_unload()

    def _register_commands(self) -> None:
        """Register all music commands to the plugin."""
        # Get all command functions from command modules
        playback_commands = setup_playback_commands(self)
        nowplaying_commands = setup_nowplaying_commands(self)
        queue_commands = setup_queue_commands(self)
        voice_commands = setup_voice_commands(self)
        search_commands = setup_search_commands(self)
        settings_commands = setup_settings_commands(self)
        history_commands = setup_history_commands(self)

        # Register all commands
        all_commands = (
            playback_commands
            + nowplaying_commands
            + queue_commands
            + voice_commands
            + search_commands
            + settings_commands
            + history_commands
        )

        for command_func in all_commands:
            # The command decorator has already been applied to these functions
            # We just need to add them to our plugin
            setattr(self, command_func.__name__, command_func)

    async def _save_queue_to_db(self, guild_id: int) -> None:
        """Save the current queue to database for persistence."""
        await save_queue_to_db(self, guild_id)

    async def _add_to_history(self, guild_id: int, track) -> None:
        """Add a track to the guild's music history."""
        await add_to_history(self, guild_id, track)

    # Web Panel Implementation
    def get_panel_info(self) -> dict[str, Any]:
        """Return metadata about this plugin's web panel."""
        return {
            "name": "Music Player",
            "description": "Music queue management and playback controls",
            "route": "/plugin/music",
            "icon": "fa-solid fa-music",
            "nav_order": 5,
        }

    def register_web_routes(self, app) -> None:
        """Register web routes for the music plugin."""
        from .web_panel import register_music_routes

        register_music_routes(app, self)
