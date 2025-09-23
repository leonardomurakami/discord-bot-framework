import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import FastAPI, Form, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from bot.database.manager import db_manager
from .models import MusicQueue, MusicSession

logger = logging.getLogger(__name__)

# WebSocket connection manager
class MusicWebSocketManager:
    def __init__(self):
        # guild_id -> set of websocket connections
        self.connections: Dict[int, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, guild_id: int):
        await websocket.accept()
        async with self.lock:
            if guild_id not in self.connections:
                self.connections[guild_id] = set()
            self.connections[guild_id].add(websocket)
        logger.debug(f"WebSocket connected for guild {guild_id}, total: {len(self.connections[guild_id])}")

    async def disconnect(self, websocket: WebSocket, guild_id: int):
        async with self.lock:
            if guild_id in self.connections:
                self.connections[guild_id].discard(websocket)
                if not self.connections[guild_id]:
                    del self.connections[guild_id]
        logger.debug(f"WebSocket disconnected for guild {guild_id}")

    async def broadcast_to_guild(self, guild_id: int, message: dict):
        if guild_id not in self.connections:
            return

        # Create a copy of connections to avoid modification during iteration
        async with self.lock:
            connections_copy = self.connections[guild_id].copy()

        disconnected = set()
        for websocket in connections_copy:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.debug(f"Failed to send WebSocket message: {e}")
                disconnected.add(websocket)

        # Remove disconnected websockets
        if disconnected:
            async with self.lock:
                if guild_id in self.connections:
                    self.connections[guild_id] -= disconnected
                    if not self.connections[guild_id]:
                        del self.connections[guild_id]

# Global WebSocket manager instance
music_ws_manager = MusicWebSocketManager()


async def get_music_status_data(guild_id: int, plugin) -> dict:
    """Get music status data for a guild. Used by both REST API and WebSocket."""
    try:
        # Check if lavalink client is available
        if not plugin.lavalink_client:
            return {
                "connected": False,
                "playing": False,
                "paused": False,
                "position": 0,
                "volume": 50,
                "repeat_mode": "off",
                "shuffle_enabled": False,
                "current_track": None,
                "queue": [],
                "queue_duration": 0,
                "error": "Lavalink client not connected"
            }

        player = plugin.lavalink_client.player_manager.get(guild_id)

        # If no player exists, return disconnected state
        if not player:
            return {
                "connected": False,
                "playing": False,
                "paused": False,
                "position": 0,
                "volume": 50,
                "repeat_mode": "off",
                "shuffle_enabled": False,
                "current_track": None,
                "queue": [],
                "queue_duration": 0,
            }

        # Get repeat mode from plugin state
        repeat_mode = "off"
        if guild_id in plugin.repeat_modes:
            repeat_value = plugin.repeat_modes[guild_id]
            if repeat_value == 1:
                repeat_mode = "track"
            elif repeat_value == 2:
                repeat_mode = "queue"

        # Get shuffle setting from database (only place we store this)
        shuffle_enabled = False
        try:
            async with db_manager.session() as session:
                from sqlalchemy import select
                session_result = await session.execute(select(MusicSession).filter_by(guild_id=guild_id))
                music_session = session_result.scalar_one_or_none()
                if music_session:
                    shuffle_enabled = music_session.shuffle_enabled
        except Exception:
            # If database query fails, default to False
            pass

        # Build status entirely from Lavalink player state
        status = {
            "connected": player.is_connected,
            "playing": player.is_playing,
            "paused": player.paused,
            "position": player.position,
            "volume": player.volume,
            "repeat_mode": repeat_mode,
            "shuffle_enabled": shuffle_enabled,
            "current_track": None,
            "queue": [],
            "queue_duration": 0,
        }

        # Get current track from Lavalink
        if player.current:
            track = player.current
            status["current_track"] = {
                "title": track.title,
                "author": track.author,
                "duration": track.duration,
                "position": player.position,
                "uri": track.uri,
                "requester_id": getattr(track, 'requester', 0),
            }

        # Get queue from Lavalink (this is the live, authoritative queue)
        queue_duration = 0
        if player.queue:
            for i, queue_track in enumerate(player.queue):
                queue_duration += queue_track.duration
                status["queue"].append({
                    "position": i,
                    "title": queue_track.title,
                    "author": queue_track.author,
                    "duration": queue_track.duration,
                    "uri": queue_track.uri,
                    "requester_id": getattr(queue_track, 'requester', 0),
                })

        status["queue_duration"] = queue_duration
        return status

    except Exception as e:
        logger.error(f"Error getting music status for guild {guild_id}: {e}")
        return {
            "connected": False,
            "playing": False,
            "paused": False,
            "position": 0,
            "volume": 50,
            "repeat_mode": "off",
            "shuffle_enabled": False,
            "current_track": None,
            "queue": [],
            "queue_duration": 0,
            "error": str(e)
        }


async def broadcast_music_update(guild_id: int, plugin, update_type: str = "status_update"):
    """Broadcast music status update to all connected WebSocket clients for a guild."""
    try:
        status = await get_music_status_data(guild_id, plugin)
        await music_ws_manager.broadcast_to_guild(guild_id, {
            "type": update_type,
            "data": status
        })
    except Exception as e:
        logger.error(f"Error broadcasting music update for guild {guild_id}: {e}")


def register_music_routes(app: FastAPI, plugin) -> None:
    """Register all music web routes."""

    @app.get("/plugin/music", response_class=HTMLResponse)
    async def music_panel(request: Request):
        """Main music panel interface."""
        return plugin.render_plugin_template(request, "panel.html")

    @app.websocket("/ws/music/{guild_id}")
    async def music_websocket(websocket: WebSocket, guild_id: int):
        """WebSocket endpoint for real-time music updates."""
        await music_ws_manager.connect(websocket, guild_id)
        try:
            # Send initial status
            try:
                status = await get_music_status_data(guild_id, plugin)
                await websocket.send_text(json.dumps({
                    "type": "status_update",
                    "data": status
                }))
            except Exception as e:
                logger.error(f"Error sending initial status: {e}")

            # Keep connection alive and handle incoming messages
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    # Handle ping/pong for keepalive
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))

                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    break

        except WebSocketDisconnect:
            pass
        finally:
            await music_ws_manager.disconnect(websocket, guild_id)

    @app.get("/api/music/status/{guild_id}")
    async def get_music_status(guild_id: int):
        """Get current music status for a guild."""
        try:
            status = await get_music_status_data(guild_id, plugin)
            if "error" in status:
                if status["error"] == "Lavalink client not connected":
                    raise HTTPException(status_code=503, detail=status["error"])
                else:
                    raise HTTPException(status_code=500, detail=status["error"])
            return JSONResponse(status)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting music status for guild {guild_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/music/play")
    async def add_track(request: Request, query: str = Form(...), guild_id: int = Form(...), source: str = Form(default="ytsearch")):
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
                # Validate source
                valid_sources = ["ytsearch", "ytmsearch", "spsearch", "amsearch", "scsearch", "dzsearch"]
                if source not in valid_sources:
                    source = "ytsearch"
                query = f"{source}:{query}"

            results = await plugin.lavalink_client.get_tracks(query)

            if not results.tracks:
                return HTMLResponse("❌ <strong>No tracks found</strong>")

            track = results.tracks[0]
            player.add(requester=0, track=track)  # Using 0 as web requester ID

            if not player.is_playing:
                await player.play()

            # Save queue to database
            await plugin._save_queue_to_db(guild_id)

            # Broadcast update to WebSocket clients
            await broadcast_music_update(guild_id, plugin, "queue_update")

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

            response_html = ""
            should_broadcast = False

            if action == "play":
                if player.paused:
                    await player.set_pause(False)
                    response_html = "▶️ <strong>Resumed playback</strong>"
                    should_broadcast = True
                elif not player.is_playing and player.queue:
                    await player.play()
                    response_html = "▶️ <strong>Started playback</strong>"
                    should_broadcast = True
                else:
                    response_html = "ℹ️ <strong>Already playing</strong>"

            elif action == "pause":
                if player.is_playing:
                    await player.set_pause(True)
                    response_html = "⏸️ <strong>Paused playback</strong>"
                    should_broadcast = True
                else:
                    response_html = "ℹ️ <strong>Not currently playing</strong>"

            elif action == "stop":
                await player.stop()
                player.queue.clear()
                await plugin._save_queue_to_db(guild_id)
                response_html = "⏹️ <strong>Stopped and cleared queue</strong>"
                should_broadcast = True

            elif action == "skip":
                if player.current:
                    # Check repeat mode before skipping
                    repeat_mode = plugin.repeat_modes.get(guild_id, 0)

                    # Handle repeat track mode explicitly
                    if repeat_mode == 1:
                        # Add the current track back to the front of the queue for repeat track
                        player.add(track=player.current, index=0)

                    await player.skip()

                    # Small delay to ensure skip is processed
                    import asyncio
                    await asyncio.sleep(0.1)

                    # Ensure playback continues if we have tracks in queue
                    if not player.is_playing and player.queue:
                        await player.play()

                    await plugin._save_queue_to_db(guild_id)
                    response_html = "⏭️ <strong>Skipped track</strong>"
                    should_broadcast = True
                else:
                    response_html = "ℹ️ <strong>No track to skip</strong>"

            elif action == "previous":
                # This would require implementing a history system
                response_html = "ℹ️ <strong>Previous track not available</strong>"

            else:
                response_html = "❌ <strong>Unknown action</strong>"

            # Broadcast update to WebSocket clients if state changed
            if should_broadcast:
                await broadcast_music_update(guild_id, plugin, "playback_update")

            return HTMLResponse(response_html)

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

            # Broadcast update to WebSocket clients
            await broadcast_music_update(guild_id, plugin, "volume_update")

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

            # Broadcast update to WebSocket clients
            await broadcast_music_update(guild_id, plugin, "repeat_update")

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

            # Broadcast update to WebSocket clients
            await broadcast_music_update(guild_id, plugin, "shuffle_update")

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

            # Broadcast update to WebSocket clients
            await broadcast_music_update(guild_id, plugin, "queue_update")

            return HTMLResponse(f"🗑️ <strong>Removed:</strong> {removed_track.title}")

        except Exception as e:
            logger.error(f"Error removing from queue: {e}")
            return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

    @app.post("/api/music/queue/reorder")
    async def reorder_queue(guild_id: int = Form(...), from_position: int = Form(...), to_position: int = Form(...)):
        """Reorder a track in the queue by moving it from one position to another."""
        try:
            # Check if lavalink client is available
            if not plugin.lavalink_client:
                return JSONResponse({"success": False, "error": "Lavalink client not connected"}, status_code=503)

            player = plugin.lavalink_client.player_manager.get(guild_id)

            if not player or not player.is_connected:
                return JSONResponse({"success": False, "error": "Bot not connected to voice channel"}, status_code=400)

            queue_length = len(player.queue)
            if from_position < 0 or from_position >= queue_length:
                return JSONResponse({"success": False, "error": "Invalid source position"}, status_code=400)

            if to_position < 0 or to_position >= queue_length:
                return JSONResponse({"success": False, "error": "Invalid target position"}, status_code=400)

            if from_position == to_position:
                return JSONResponse({"success": True, "message": "No change needed"})

            # Remove track from original position
            track = player.queue.pop(from_position)

            # Insert track at new position
            player.queue.insert(to_position, track)

            # Save queue to database
            await plugin._save_queue_to_db(guild_id)

            # Broadcast update to WebSocket clients
            await broadcast_music_update(guild_id, plugin, "queue_reorder")

            return JSONResponse({
                "success": True,
                "message": f"Moved '{track.title}' from position {from_position + 1} to {to_position + 1}"
            })

        except Exception as e:
            logger.error(f"Error reordering queue: {e}")
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)

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

    @app.get("/api/music/search/suggestions")
    async def get_search_suggestions(query: str = Query(..., min_length=2), source: str = Query(default="ytsearch")):
        """Get search suggestions for track search."""
        try:
            if len(query.strip()) < 2:
                return JSONResponse([])

            # Check if it's a URL - don't provide suggestions for URLs
            if query.startswith(("http://", "https://", "www.")):
                return JSONResponse([])

            # Check if lavalink client is available
            if not plugin.lavalink_client:
                return JSONResponse([])

            # Validate source
            valid_sources = ["ytsearch", "ytmsearch", "spsearch", "amsearch", "scsearch", "dzsearch"]
            if source not in valid_sources:
                source = "ytsearch"

            # Search for tracks using specified source
            search_query = f"{source}:{query}"
            results = await plugin.lavalink_client.get_tracks(search_query)

            if not results.tracks:
                return JSONResponse([])

            # Format suggestions - limit to top 8 results
            suggestions = []
            for track in results.tracks[:8]:
                duration_mins = track.duration // 60000
                duration_secs = (track.duration % 60000) // 1000

                # Extract thumbnail URL based on source
                thumbnail_url = None
                if track.uri:
                    import re
                    if "youtube" in track.uri:
                        youtube_id_match = re.search(r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})', track.uri)
                        if youtube_id_match:
                            video_id = youtube_id_match.group(1)
                            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                    elif "soundcloud" in track.uri:
                        # SoundCloud tracks might have artwork_url in track metadata
                        thumbnail_url = getattr(track, 'artwork_url', None)
                    # For other sources (Spotify, Apple Music, etc.), we'll use a default icon

                suggestions.append({
                    "title": track.title,
                    "author": track.author,
                    "duration": f"{duration_mins:02d}:{duration_secs:02d}",
                    "uri": track.uri,
                    "thumbnail": thumbnail_url,
                    "source": source,
                    "display": f"{track.title} - {track.author}"
                })

            return JSONResponse(suggestions)

        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return JSONResponse([])

    @app.get("/api/music/sources")
    async def get_available_sources():
        """Get available music sources from Lavalink."""
        try:
            # Check if lavalink client is available
            if not plugin.lavalink_client:
                # Return default sources if Lavalink is not connected
                return JSONResponse([{
                    "id": "ytsearch",
                    "name": "YouTube",
                    "icon": "fab fa-youtube",
                    "available": False
                }])

            # Get available sources from Lavalink client
            available_sources = []

            # Define all possible sources with their metadata
            source_definitions = [
                {
                    "id": "ytsearch",
                    "name": "YouTube",
                    "icon": "fab fa-youtube",
                    "description": "YouTube videos"
                },
                {
                    "id": "ytmsearch",
                    "name": "YouTube Music",
                    "icon": "fab fa-youtube",
                    "description": "YouTube Music tracks"
                },
                {
                    "id": "spsearch",
                    "name": "Spotify",
                    "icon": "fab fa-spotify",
                    "description": "Spotify tracks"
                },
                {
                    "id": "amsearch",
                    "name": "Apple Music",
                    "icon": "fab fa-apple",
                    "description": "Apple Music tracks"
                },
                {
                    "id": "scsearch",
                    "name": "SoundCloud",
                    "icon": "fab fa-soundcloud",
                    "description": "SoundCloud tracks"
                },
                {
                    "id": "dzsearch",
                    "name": "Deezer",
                    "icon": "fas fa-music",
                    "description": "Deezer tracks"
                }
            ]

            # Test each source with a simple query to check availability
            for source_def in source_definitions:
                try:
                    # Test with a simple query to see if source responds
                    test_query = f"{source_def['id']}:test"
                    test_result = await plugin.lavalink_client.get_tracks(test_query)

                    # If we get a result (even empty), the source is available
                    source_def["available"] = True
                    logger.debug(f"Source {source_def['id']} is available")
                except Exception as e:
                    source_def["available"] = False
                    logger.debug(f"Source {source_def['id']} is not available: {e}")

                # Only include available sources
                if source_def["available"]:
                    available_sources.append(source_def)

            # Always include at least YouTube as a fallback if nothing else works
            if not available_sources:
                youtube_source = next((s for s in source_definitions if s["id"] == "ytsearch"), None)
                if youtube_source:
                    youtube_source["available"] = True
                    available_sources.append(youtube_source)

            return JSONResponse(available_sources)

        except Exception as e:
            logger.error(f"Error getting available sources: {e}")
            # Return YouTube as fallback
            return JSONResponse([{
                "id": "ytsearch",
                "name": "YouTube",
                "icon": "fab fa-youtube",
                "description": "YouTube videos",
                "available": True
            }])
