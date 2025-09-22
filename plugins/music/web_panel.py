import logging

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bot.database.manager import db_manager
from bot.database.models import MusicQueue, MusicSession

logger = logging.getLogger(__name__)


def register_music_routes(app: FastAPI, plugin) -> None:
    """Register all music web routes."""

    @app.get("/plugin/music", response_class=HTMLResponse)
    async def music_panel(request: Request):
        """Main music panel interface."""
        return plugin.render_plugin_template(request, "panel.html")

    @app.get("/api/music/status/{guild_id}")
    async def get_music_status(guild_id: int):
        """Get current music status for a guild."""
        try:
            # Check if lavalink client is available
            if not plugin.lavalink_client:
                raise HTTPException(status_code=503, detail="Lavalink client not connected")

            player = plugin.lavalink_client.player_manager.get(guild_id)

            # Get queue from database
            async with db_manager.session() as session:
                from sqlalchemy import select

                queue_result = await session.execute(select(MusicQueue).filter_by(guild_id=guild_id).order_by(MusicQueue.position))
                queue_tracks = queue_result.scalars().all()

                session_result = await session.execute(select(MusicSession).filter_by(guild_id=guild_id))
                music_session = session_result.scalar_one_or_none()

            status = {
                "connected": player is not None and player.is_connected,
                "playing": player.is_playing if player else False,
                "paused": player.paused if player else False,
                "position": player.position if player else 0,
                "volume": player.volume if player else 50,
                "repeat_mode": music_session.repeat_mode if music_session else "off",
                "shuffle_enabled": music_session.shuffle_enabled if music_session else False,
                "current_track": None,
                "queue": [],
                "queue_duration": 0,
            }

            if player and player.current:
                track = player.current
                status["current_track"] = {
                    "title": track.title,
                    "author": track.author,
                    "duration": track.duration,
                    "position": player.position,
                    "uri": track.uri,
                }

            # Convert queue tracks to dict format
            queue_duration = 0
            for track in queue_tracks:
                queue_duration += track.track_duration
                status["queue"].append(
                    {
                        "position": track.position,
                        "title": track.track_title,
                        "author": track.track_author,
                        "duration": track.track_duration,
                        "uri": track.track_uri,
                        "requester_id": track.requester_id,
                    }
                )

            status["queue_duration"] = queue_duration

            return JSONResponse(status)

        except Exception as e:
            logger.error(f"Error getting music status for guild {guild_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/music/play")
    async def add_track(request: Request, query: str = Form(...), guild_id: int = Form(...)):
        """Add a track to the queue."""
        try:
            # Check if lavalink client is available
            if not plugin.lavalink_client:
                return HTMLResponse("❌ <strong>Lavalink client not connected</strong>")

            player = plugin.lavalink_client.player_manager.get(guild_id)

            if not player or not player.is_connected:
                return HTMLResponse("❌ <strong>Bot not connected to voice channel</strong>")

            # Search for tracks
            if not query.startswith(("http://", "https://")):
                query = f"ytsearch:{query}"

            results = await plugin.lavalink_client.get_tracks(query)

            if not results.tracks:
                return HTMLResponse("❌ <strong>No tracks found</strong>")

            track = results.tracks[0]
            player.add(requester=0, track=track)  # Using 0 as web requester ID

            if not player.is_playing:
                await player.play()

            # Save queue to database
            await plugin._save_queue_to_db(guild_id)

            return HTMLResponse(f"✅ <strong>Added:</strong> {track.title} by {track.author}")

        except Exception as e:
            logger.error(f"Error adding track: {e}")
            return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

    @app.post("/api/music/controls/{action}")
    async def playback_controls(action: str, guild_id: int = Form(...)):
        """Handle playback control actions."""
        try:
            # Check if lavalink client is available
            if not plugin.lavalink_client:
                return HTMLResponse("❌ <strong>Lavalink client not connected</strong>")

            player = plugin.lavalink_client.player_manager.get(guild_id)

            if not player:
                return HTMLResponse("❌ <strong>No player found</strong>")

            if action == "play":
                if player.paused:
                    await player.set_pause(False)
                    return HTMLResponse("▶️ <strong>Resumed playback</strong>")
                elif not player.is_playing and player.queue:
                    await player.play()
                    return HTMLResponse("▶️ <strong>Started playback</strong>")
                else:
                    return HTMLResponse("ℹ️ <strong>Already playing</strong>")

            elif action == "pause":
                if player.is_playing:
                    await player.set_pause(True)
                    return HTMLResponse("⏸️ <strong>Paused playback</strong>")
                else:
                    return HTMLResponse("ℹ️ <strong>Not currently playing</strong>")

            elif action == "stop":
                await player.stop()
                player.queue.clear()
                await plugin._save_queue_to_db(guild_id)
                return HTMLResponse("⏹️ <strong>Stopped and cleared queue</strong>")

            elif action == "skip":
                if player.current:
                    await player.skip()
                    await plugin._save_queue_to_db(guild_id)
                    return HTMLResponse("⏭️ <strong>Skipped track</strong>")
                else:
                    return HTMLResponse("ℹ️ <strong>No track to skip</strong>")

            elif action == "previous":
                # This would require implementing a history system
                return HTMLResponse("ℹ️ <strong>Previous track not available</strong>")

            else:
                return HTMLResponse("❌ <strong>Unknown action</strong>")

        except Exception as e:
            logger.error(f"Error with playback control {action}: {e}")
            return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

    @app.post("/api/music/volume")
    async def set_volume(guild_id: int = Form(...), volume: int = Form(...)):
        """Set player volume."""
        try:
            if not 0 <= volume <= 150:
                return HTMLResponse("❌ <strong>Volume must be between 0 and 150</strong>")

            # Check if lavalink client is available
            if not plugin.lavalink_client:
                return HTMLResponse("❌ <strong>Lavalink client not connected</strong>")

            player = plugin.lavalink_client.player_manager.get(guild_id)

            if not player:
                return HTMLResponse("❌ <strong>No player found</strong>")

            await player.set_volume(volume)

            # Update session in database
            async with db_manager.session() as session:
                from sqlalchemy import select

                session_result = await session.execute(select(MusicSession).filter_by(guild_id=guild_id))
                music_session = session_result.scalar_one_or_none()
                if music_session:
                    music_session.volume = volume
                    await session.commit()

            return HTMLResponse(f"🔊 <strong>Volume set to {volume}%</strong>")

        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

    @app.post("/api/music/repeat")
    async def set_repeat_mode(guild_id: int = Form(...), mode: str = Form(...)):
        """Set repeat mode."""
        try:
            if mode not in ["off", "track", "queue"]:
                return HTMLResponse("❌ <strong>Invalid repeat mode</strong>")

            # Update session in database
            async with db_manager.session() as session:
                from sqlalchemy import select

                session_result = await session.execute(select(MusicSession).filter_by(guild_id=guild_id))
                music_session = session_result.scalar_one_or_none()
                if not music_session:
                    # Create new session if it doesn't exist
                    music_session = MusicSession(
                        guild_id=guild_id,
                        voice_channel_id=0,  # Will be updated when bot connects
                        text_channel_id=0,  # Will be updated when bot connects
                        repeat_mode=mode,
                    )
                    session.add(music_session)
                else:
                    music_session.repeat_mode = mode
                await session.commit()

            # Update plugin's repeat modes
            if mode == "off":
                plugin.repeat_modes[guild_id] = 0
            elif mode == "track":
                plugin.repeat_modes[guild_id] = 1
            elif mode == "queue":
                plugin.repeat_modes[guild_id] = 2

            mode_text = {"off": "Off", "track": "Track", "queue": "Queue"}[mode]
            return HTMLResponse(f"🔁 <strong>Repeat mode set to {mode_text}</strong>")

        except Exception as e:
            logger.error(f"Error setting repeat mode: {e}")
            return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

    @app.post("/api/music/shuffle")
    async def toggle_shuffle(guild_id: int = Form(...)):
        """Toggle shuffle mode."""
        try:
            async with db_manager.session() as session:
                from sqlalchemy import select

                session_result = await session.execute(select(MusicSession).filter_by(guild_id=guild_id))
                music_session = session_result.scalar_one_or_none()
                if not music_session:
                    music_session = MusicSession(
                        guild_id=guild_id,
                        voice_channel_id=0,  # Will be updated when bot connects
                        text_channel_id=0,  # Will be updated when bot connects
                        shuffle_enabled=True,
                    )
                    session.add(music_session)
                    enabled = True
                else:
                    enabled = not music_session.shuffle_enabled
                    music_session.shuffle_enabled = enabled
                await session.commit()

            status = "enabled" if enabled else "disabled"
            return HTMLResponse(f"🔀 <strong>Shuffle {status}</strong>")

        except Exception as e:
            logger.error(f"Error toggling shuffle: {e}")
            return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

    @app.post("/api/music/queue/remove")
    async def remove_from_queue(guild_id: int = Form(...), position: int = Form(...)):
        """Remove a track from the queue."""
        try:
            # Check if lavalink client is available
            if not plugin.lavalink_client:
                return HTMLResponse("❌ <strong>Lavalink client not connected</strong>")

            player = plugin.lavalink_client.player_manager.get(guild_id)

            if not player or not player.is_connected:
                return HTMLResponse("❌ <strong>Bot not connected to voice channel</strong>")

            if position < 0 or position >= len(player.queue):
                return HTMLResponse("❌ <strong>Invalid queue position</strong>")

            removed_track = player.queue[position]
            del player.queue[position]

            await plugin._save_queue_to_db(guild_id)

            return HTMLResponse(f"🗑️ <strong>Removed:</strong> {removed_track.title}")

        except Exception as e:
            logger.error(f"Error removing from queue: {e}")
            return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

    async def _render_queue_html(guild_id: int) -> HTMLResponse:
        try:
            if not plugin.lavalink_client:
                return HTMLResponse('<div class="info-box error">Lavalink client not connected</div>')

            player = plugin.lavalink_client.player_manager.get(guild_id)

            if not player or not player.is_connected:
                return HTMLResponse('<div class="info-box error">Bot not connected to voice channel</div>')

            logger.info(
                "Queue debug for guild %s: player=%s, queue_length=%s, current=%s",
                guild_id,
                player,
                len(player.queue) if player and player.queue else 0,
                player.current.title if player and player.current else None,
            )

            if not player.queue:
                return HTMLResponse('<div class="empty-queue"><p>Queue is empty</p><p>Add some tracks to get started!</p></div>')

            html = '<div class="queue-list">'

            for i, track in enumerate(player.queue):
                duration_mins = track.duration // 60000
                duration_secs = (track.duration % 60000) // 1000

                import html as html_module

                title = html_module.escape(str(track.title))
                author = html_module.escape(str(track.author))

                html += f"""
                <div class="queue-item" data-position="{i}">
                    <div class="queue-item-info">
                        <div class="queue-item-title">{title}</div>
                        <div class="queue-item-author">{author}</div>
                    </div>
                    <div class="queue-item-duration">{duration_mins:02d}:{duration_secs:02d}</div>
                    <button type="button"
                            hx-post="/api/music/queue/remove"
                            hx-vals='{{"guild_id": {guild_id}, "position": {i}}}'
                            hx-target="#queue-result"
                            class="btn-remove">🗑️</button>
                </div>
                """

            html += "</div>"
            return HTMLResponse(html)

        except Exception as e:
            logger.error(f"Error getting queue HTML: {e}")
            return HTMLResponse(f'<div class="info-box error">Error loading queue: {str(e)}</div>')

    @app.get("/api/music/queue/{guild_id}")
    async def get_queue_html_path(guild_id: str):
        raw_guild_id = guild_id.strip()

        if not raw_guild_id.isdigit():
            logger.debug("Ignoring queue request without concrete guild id: %s", guild_id)
            return HTMLResponse('<div class="empty-queue"><p>Select a server to view the queue.</p></div>')

        return await _render_queue_html(int(raw_guild_id))

    @app.get("/api/music/queue")
    async def get_queue_html_query(guild_id: int = Query(...)):
        return await _render_queue_html(guild_id)
