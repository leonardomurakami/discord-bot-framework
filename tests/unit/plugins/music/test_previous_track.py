"""Tests for the previous-track web control."""

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.music.web.routes import register_music_routes
from tests.unit.plugins.music.conftest import TEST_SECRET_KEY

GUILD_ID = 123456789


def _build_test_client(player=None, history_tracks=None):
    """Build a TestClient with mocked auth, lavalink, and db session."""
    auth = MagicMock()
    auth.is_configured.return_value = True
    auth.is_authenticated.return_value = True
    auth.get_current_user.return_value = {
        "user": {"id": "111111"},
        "guilds": [{"id": str(GUILD_ID), "name": "Test", "permissions": 0}],
        "access_token": "tok",
    }

    plugin = MagicMock()
    plugin.name = "music"
    plugin.repeat_modes = {}
    plugin.web_panel = MagicMock()
    plugin.web_panel.web_app = MagicMock()
    plugin.web_panel.web_app.auth = auth

    if player is None:
        player = MagicMock()
    player.is_connected = True
    player.is_playing = True
    player.paused = False
    player.position = 0
    player.volume = 50
    player.queue = []
    current = MagicMock()
    current.title = "Current Track"
    current.uri = "https://example.com/current"
    current.duration = 300000
    current.author = "Artist"
    player.current = current
    player.skip = AsyncMock()
    player.add = MagicMock()
    player.stop = AsyncMock()
    player.set_pause = AsyncMock()
    player.play = AsyncMock()

    lavalink_client = MagicMock()
    lavalink_client.player_manager.get.return_value = player
    lavalink_client.player_manager.create.return_value = player
    lavalink_client.get_tracks = AsyncMock()
    plugin.lavalink_client = lavalink_client
    plugin._save_queue_to_db = AsyncMock()

    # Mock db_manager.session to return history tracks
    mock_session = AsyncMock()

    # Build scalars().all() chain for history query
    scalars_mock = MagicMock()
    if history_tracks is not None:
        scalars_mock.all.return_value = history_tracks
    else:
        scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute = AsyncMock(return_value=result_mock)

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    import plugins.music.web.routes as routes_mod

    original_session = routes_mod.db_manager.session
    routes_mod.db_manager.session = MagicMock(return_value=session_cm)

    app = FastAPI()
    register_music_routes(app, plugin)

    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(SessionMiddleware, secret_key=TEST_SECRET_KEY)  # noqa: S105
    client = TestClient(app)

    # Seed session cookie
    tmp_app = FastAPI()
    tmp_app.add_middleware(SessionMiddleware, secret_key=TEST_SECRET_KEY)  # noqa: S105

    @tmp_app.get("/_set")
    def _set(request):
        request.session.update(
            {
                "authenticated": True,
                "user": {"id": "111111"},
                "guilds": [{"id": str(GUILD_ID), "name": "Test", "permissions": 0}],
                "access_token": "tok",
            }
        )
        return {"ok": True}

    tmp_client = TestClient(tmp_app)
    resp = tmp_client.get("/_set")
    cookie = resp.headers.get("set-cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("session="):
            client.cookies["session"] = part[len("session=") :]
            break

    client.plugin = plugin
    client.player = player
    client.lavalink_client = lavalink_client
    client._restore_session = lambda: setattr(routes_mod, "db_manager", type("Tmp", (), {"session": original_session})())
    return client


class TestPreviousTrack:
    """Test history-backed previous-track and empty-history response."""

    def test_previous_track_empty_history(self):
        """When no history exists, return informational 'No previous track available'."""
        client = _build_test_client(history_tracks=[])
        resp = client.post("/api/music/controls/previous", data={"guild_id": GUILD_ID})
        assert resp.status_code == 200
        assert "No previous track available" in resp.text
        client.player.skip.assert_not_called()

    def test_previous_track_with_history(self):
        """When history exists, play the most recent entry and broadcast."""
        history_entry = MagicMock()
        history_entry.track_uri = "https://example.com/old-track"
        history_entry.track_title = "Old Track"
        history_entry.requester_id = 111111
        history_entry.position = -1

        client = _build_test_client(history_tracks=[history_entry])

        # Mock get_tracks to return a track
        track = MagicMock()
        track.title = "Old Track"
        track.uri = "https://example.com/old-track"
        track.duration = 200000
        track.author = "Artist"
        search_result = MagicMock()
        search_result.tracks = [track]
        client.lavalink_client.get_tracks = AsyncMock(return_value=search_result)

        resp = client.post("/api/music/controls/previous", data={"guild_id": GUILD_ID})
        assert resp.status_code == 200
        assert "Playing previous track" in resp.text
        client.player.add.assert_called_once()
        client.player.skip.assert_called_once()
        client.plugin._save_queue_to_db.assert_called_once_with(GUILD_ID)

    def test_previous_track_filters_current(self):
        """Previous track should skip history entries matching the current track URI."""
        # History has only the current track
        history_entry = MagicMock()
        history_entry.track_uri = "https://example.com/current"  # Same as current
        history_entry.track_title = "Current Track"
        history_entry.requester_id = 111111
        history_entry.position = -1

        client = _build_test_client(history_tracks=[history_entry])
        resp = client.post("/api/music/controls/previous", data={"guild_id": GUILD_ID})
        assert resp.status_code == 200
        assert "No previous track available" in resp.text
        client.player.skip.assert_not_called()
