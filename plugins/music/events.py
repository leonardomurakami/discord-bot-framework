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

    @lavalink.listener(lavalink.TrackEndEvent)
    async def track_end(self, event: lavalink.TrackEndEvent):
        logger.debug(f"Track finished on guild: {event.player.guild_id}")

        guild_id = event.player.guild_id
        repeat_mode = self.music_plugin.repeat_modes.get(guild_id, 0)

        if repeat_mode == 1:
            if event.track:
                event.player.add(track=event.track, index=0)
        elif repeat_mode == 2 and event.track:
            event.player.add(track=event.track)

    @lavalink.listener(lavalink.TrackExceptionEvent)
    async def track_exception(self, event: lavalink.TrackExceptionEvent):
        logger.warning(f"Track exception event happened on guild: {event.player.guild_id}")

    @lavalink.listener(lavalink.QueueEndEvent)
    async def queue_finish(self, event: lavalink.QueueEndEvent):
        logger.debug(f"Queue finished on guild: {event.player.guild_id}")
