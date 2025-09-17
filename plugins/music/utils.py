import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .music_plugin import MusicPlugin

logger = logging.getLogger(__name__)


async def save_queue_to_db(music_plugin: 'MusicPlugin', guild_id: int) -> None:
    """Save the current queue to database for persistence."""
    if guild_id in music_plugin._restoring_queues:
        return

    try:
        player = music_plugin.lavalink_client.player_manager.get(guild_id)
        if not player:
            return

        async with music_plugin.bot.db.session() as session:
            from bot.database.models import MusicQueue, MusicSession
            from sqlalchemy import text

            await session.execute(
                text("DELETE FROM music_queues WHERE guild_id = :guild_id"),
                {"guild_id": guild_id}
            )

            for position, track in enumerate(player.queue):
                queue_entry = MusicQueue(
                    guild_id=guild_id,
                    position=position,
                    track_identifier=track.identifier,
                    track_title=track.title,
                    track_author=track.author,
                    track_duration=track.duration,
                    track_uri=track.uri,
                    requester_id=track.requester
                )
                session.add(queue_entry)

            session_data = await session.get(MusicSession, guild_id)
            if session_data:
                session_data.is_playing = player.is_playing
                session_data.is_paused = player.paused
                session_data.volume = player.volume
                repeat_mode = music_plugin.repeat_modes.get(guild_id, 0)
                session_data.repeat_mode = "off" if repeat_mode == 0 else ("track" if repeat_mode == 1 else "queue")
                session_data.current_track_position = player.position
                session_data.last_activity = datetime.utcnow()
            else:
                repeat_mode = music_plugin.repeat_modes.get(guild_id, 0)
                session_data = MusicSession(
                    guild_id=guild_id,
                    voice_channel_id=player.channel_id or 0,
                    text_channel_id=0,
                    is_playing=player.is_playing,
                    is_paused=player.paused,
                    volume=player.volume,
                    repeat_mode="off" if repeat_mode == 0 else ("track" if repeat_mode == 1 else "queue"),
                    current_track_position=player.position
                )
                session.add(session_data)

            await session.commit()
            logger.debug(f"Saved queue for guild {guild_id}: {len(player.queue)} tracks")

    except Exception as e:
        logger.error(f"Error saving queue for guild {guild_id}: {e}")


async def restore_queue_from_db(music_plugin: 'MusicPlugin', guild_id: int) -> bool:
    """Restore queue from database after bot restart."""
    if guild_id in music_plugin._restoring_queues:
        return False

    try:
        music_plugin._restoring_queues.add(guild_id)

        async with music_plugin.bot.db.session() as session:
            from bot.database.models import MusicQueue, MusicSession
            from sqlalchemy import select

            session_data = await session.get(MusicSession, guild_id)
            if not session_data:
                return False

            result = await session.execute(
                select(MusicQueue)
                .where(MusicQueue.guild_id == guild_id)
                .order_by(MusicQueue.position)
            )
            queue_tracks = result.scalars().all()

            if not queue_tracks:
                return False

            player = music_plugin.lavalink_client.player_manager.create(guild_id)

            await player.set_volume(session_data.volume)
            if session_data.repeat_mode == "track":
                music_plugin.repeat_modes[guild_id] = 1
            elif session_data.repeat_mode == "queue":
                music_plugin.repeat_modes[guild_id] = 2
            else:
                music_plugin.repeat_modes[guild_id] = 0

            restored_count = 0
            for queue_track in queue_tracks:
                try:
                    search_result = await music_plugin.lavalink_client.get_tracks(queue_track.track_uri)
                    if search_result.tracks:
                        track = search_result.tracks[0]
                        track.requester = queue_track.requester_id
                        player.add(track=track)
                        restored_count += 1
                    else:
                        logger.warning(f"Could not restore track: {queue_track.track_title}")
                except Exception as e:
                    logger.error(f"Error restoring track {queue_track.track_title}: {e}")

            logger.debug(f"Restored queue for guild {guild_id}: {restored_count}/{len(queue_tracks)} tracks")
            return restored_count > 0

    except Exception as e:
        logger.error(f"Error restoring queue for guild {guild_id}: {e}")
        return False
    finally:
        music_plugin._restoring_queues.discard(guild_id)


async def clear_queue_from_db(music_plugin: 'MusicPlugin', guild_id: int) -> None:
    """Clear queue from database when player is stopped."""
    try:
        async with music_plugin.bot.db.session() as session:
            from sqlalchemy import text

            await session.execute(
                text("DELETE FROM music_queues WHERE guild_id = :guild_id"),
                {"guild_id": guild_id}
            )
            await session.execute(
                text("DELETE FROM music_sessions WHERE guild_id = :guild_id"),
                {"guild_id": guild_id}
            )
            await session.commit()
            logger.debug(f"Cleared persistent queue for guild {guild_id}")
    except Exception as e:
        logger.error(f"Error clearing queue from database for guild {guild_id}: {e}")


async def restore_all_queues(music_plugin: 'MusicPlugin') -> None:
    """Restore all queues from database on bot startup."""
    try:
        await asyncio.sleep(5)

        async with music_plugin.bot.db.session() as session:
            from bot.database.models import MusicSession
            from sqlalchemy import select

            result = await session.execute(
                select(MusicSession.guild_id).distinct()
            )
            guild_ids = [row[0] for row in result.fetchall()]

            restored_count = 0
            for guild_id in guild_ids:
                try:
                    if await restore_queue_from_db(music_plugin, guild_id):
                        restored_count += 1
                except Exception as e:
                    logger.error(f"Error restoring queue for guild {guild_id}: {e}")

            if restored_count > 0:
                logger.debug(f"Restored queues for {restored_count} guilds on startup")

    except Exception as e:
        logger.error(f"Error during queue restoration: {e}")


async def add_to_history(music_plugin: 'MusicPlugin', guild_id: int, track) -> None:
    """Add a track to the guild's music history."""
    try:
        async with music_plugin.bot.db.session() as session:
            from bot.database.models import MusicQueue
            from sqlalchemy import text, exc

            # First, clean up old history entries before adding new one
            await session.execute(
                text("""DELETE FROM music_queues
                   WHERE guild_id = :guild_id AND position = -1
                   AND id NOT IN (
                       SELECT id FROM music_queues
                       WHERE guild_id = :guild_id AND position = -1
                       ORDER BY created_at DESC LIMIT 49
                   )"""),
                {"guild_id": guild_id}
            )

            # Find the next available position for history (should be negative)
            result = await session.execute(
                text("""SELECT MIN(position) FROM music_queues
                        WHERE guild_id = :guild_id AND position < 0"""),
                {"guild_id": guild_id}
            )
            min_position = result.scalar()
            next_position = min_position - 1 if min_position is not None else -1

            history_entry = MusicQueue(
                guild_id=guild_id,
                position=next_position,
                track_identifier=track.identifier,
                track_title=track.title,
                track_author=track.author,
                track_duration=track.duration,
                track_uri=track.uri,
                requester_id=track.requester,
                created_at=datetime.utcnow()
            )
            session.add(history_entry)

            await session.commit()
            logger.debug(f"Added track to history for guild {guild_id}: {track.title}")

    except exc.IntegrityError as e:
        # Handle constraint violations gracefully
        logger.debug(f"History entry already exists for guild {guild_id}, skipping: {track.title}")
    except Exception as e:
        logger.error(f"Error adding track to history for guild {guild_id}: {e}")


async def check_voice_channel_empty(music_plugin: 'MusicPlugin', guild_id: int, channel_id: int) -> None:
    """Check if voice channel is empty and start disconnect timer if needed."""
    try:
        voice_states = [
            vs for vs in music_plugin.bot.hikari_bot.cache.get_voice_states_view_for_guild(guild_id).values()
            if vs.channel_id == channel_id and not vs.member.is_bot
        ]

        if len(voice_states) == 0:
            await start_disconnect_timer(music_plugin, guild_id)
        else:
            await cancel_disconnect_timer(music_plugin, guild_id)

    except Exception as e:
        logger.error(f"Error checking voice channel: {e}")


async def start_disconnect_timer(music_plugin: 'MusicPlugin', guild_id: int) -> None:
    """Start auto-disconnect timer for a guild."""
    await cancel_disconnect_timer(music_plugin, guild_id)

    disconnect_minutes = await music_plugin.get_setting(guild_id, "auto_disconnect_timer", 5)
    disconnect_seconds = disconnect_minutes * 60

    async def disconnect_after_delay():
        await asyncio.sleep(disconnect_seconds)
        try:
            player = music_plugin.lavalink_client.player_manager.get(guild_id)
            if player and player.is_connected:
                if player.channel_id:
                    voice_states = [
                        vs for vs in music_plugin.bot.hikari_bot.cache.get_voice_states_view_for_guild(guild_id).values()
                        if vs.channel_id == player.channel_id and not vs.member.is_bot
                    ]

                    if len(voice_states) == 0:
                        await player.stop()
                        player.queue.clear()
                        await music_plugin.bot.hikari_bot.update_voice_state(guild_id, None)
                        logger.debug(f"Auto-disconnected from empty voice channel in guild {guild_id}")

            music_plugin.disconnect_timers.pop(guild_id, None)

        except Exception as e:
            logger.error(f"Error during auto-disconnect: {e}")

    task = asyncio.create_task(disconnect_after_delay())
    music_plugin.disconnect_timers[guild_id] = task


async def cancel_disconnect_timer(music_plugin: 'MusicPlugin', guild_id: int) -> None:
    """Cancel auto-disconnect timer for a guild."""
    if guild_id in music_plugin.disconnect_timers:
        task = music_plugin.disconnect_timers.pop(guild_id)
        if not task.done():
            task.cancel()


async def handle_playlist_add(music_plugin: 'MusicPlugin', ctx, search_result, player, channel_id: int) -> None:
    """Handle adding a playlist to the queue."""
    tracks = search_result.tracks

    if not player.is_connected:
        await music_plugin.bot.hikari_bot.update_voice_state(ctx.guild_id, channel_id)

    added_count = 0
    for track in tracks:
        player.add(requester=ctx.author.id, track=track)
        added_count += 1

    was_playing = player.is_playing
    if not was_playing and len(tracks) > 0:
        await player.play()

    total_duration = sum(track.duration for track in tracks)
    total_minutes = total_duration // 60000
    total_hours = total_minutes // 60
    remaining_minutes = total_minutes % 60

    embed = music_plugin.create_embed(
        title="📋 Playlist Added",
        color=music_plugin.bot.hikari_bot.get_me().accent_color or 0x00FF00
    )

    playlist_name = "Unknown Playlist"
    if hasattr(search_result, 'playlist_info') and search_result.playlist_info:
        playlist_name = getattr(search_result.playlist_info, 'name', 'Unknown Playlist') or 'Unknown Playlist'

    embed.add_field(
        name="📄 Playlist",
        value=f"**{playlist_name}**",
        inline=False
    )

    embed.add_field(
        name="🎵 Tracks Added",
        value=f"{added_count} tracks",
        inline=True
    )

    if total_hours > 0:
        duration_str = f"{total_hours}h {remaining_minutes}m"
    else:
        duration_str = f"{total_minutes}m"

    embed.add_field(
        name="⏱️ Total Duration",
        value=duration_str,
        inline=True
    )

    embed.add_field(
        name="👤 Requested by",
        value=ctx.author.mention,
        inline=True
    )

    status = "🎵 Now Playing" if not was_playing else "📋 Added to Queue"
    embed.add_field(
        name="📍 Status",
        value=status,
        inline=False
    )

    await music_plugin.smart_respond(ctx, embed=embed)