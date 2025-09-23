import logging

import lavalink

logger = logging.getLogger(__name__)


class MusicEventHandler:
    def __init__(self, music_plugin):
        self.music_plugin = music_plugin

    @lavalink.listener(lavalink.TrackStartEvent)
    async def track_start(self, event: lavalink.TrackStartEvent):
        logger.debug(f"Track started on guild: {event.player.guild_id}")

        if event.track:
            await self.music_plugin._add_to_history(event.player.guild_id, event.track)

        # Broadcast track start to WebSocket clients
        await self._broadcast_music_update(event.player.guild_id, "track_start")

    @lavalink.listener(lavalink.TrackEndEvent)
    async def track_end(self, event: lavalink.TrackEndEvent):
        logger.debug(f"Track finished on guild: {event.player.guild_id}")

        guild_id = event.player.guild_id
        repeat_mode = self.music_plugin.repeat_modes.get(guild_id, 0)

        # Only handle repeat if the track ended naturally (not manually skipped)
        # reason = FINISHED means natural end, REPLACED means skipped
        if event.reason == "FINISHED":
            if repeat_mode == 1:
                if event.track:
                    event.player.add(track=event.track, index=0)
            elif repeat_mode == 2 and event.track:
                event.player.add(track=event.track)

        # Save queue state and broadcast track end to WebSocket clients
        await self.music_plugin._save_queue_to_db(guild_id)
        await self._broadcast_music_update(guild_id, "track_end")

    @lavalink.listener(lavalink.TrackExceptionEvent)
    async def track_exception(self, event: lavalink.TrackExceptionEvent):
        logger.warning(f"Track exception event happened on guild: {event.player.guild_id}")

    @lavalink.listener(lavalink.QueueEndEvent)
    async def queue_finish(self, event: lavalink.QueueEndEvent):
        logger.debug(f"Queue finished on guild: {event.player.guild_id}")

        # Broadcast queue end to WebSocket clients
        await self._broadcast_music_update(event.player.guild_id, "queue_end")

    async def _broadcast_music_update(self, guild_id: int, update_type: str):
        """Broadcast music update to WebSocket clients."""
        try:
            from .web import broadcast_music_update
            await broadcast_music_update(guild_id, self.music_plugin, update_type)
        except Exception as e:
            logger.error(f"Error broadcasting music update for guild {guild_id}: {e}")
