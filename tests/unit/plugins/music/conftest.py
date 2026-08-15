"""Shared fixtures for music plugin tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.music.web.routes import register_music_routes

# ---------------------------------------------------------------------------
# Auth / session helpers
# ---------------------------------------------------------------------------

GUILD_ID = 123456789
OTHER_GUILD_ID = 999999999
TEST_SECRET_KEY = "test-secret-key-for-tests"  # noqa: S105 - test-only secret


class FakeSession(dict):
    """A dict-based session that behaves like Starlette's SessionMiddleware."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, key, default=None):
        return super().get(key, default)


def _make_auth(authenticated: bool, guild_ids: list[int] | None = None):
    """Create a fake DiscordAuth-like object."""
    auth = MagicMock()
    auth.is_configured.return_value = True

    if authenticated:
        guilds = [{"id": str(gid), "name": f"Guild {gid}", "permissions": 0} for gid in (guild_ids or [GUILD_ID])]
        user_info = {"id": "111111", "username": "testuser"}

        auth.is_authenticated.return_value = True
        auth.get_current_user.return_value = {
            "user": user_info,
            "guilds": guilds,
            "access_token": "fake-token",
        }
    else:
        auth.is_authenticated.return_value = False
        auth.get_current_user.return_value = None

    return auth


def _make_web_app(auth):
    """Create a fake web_panel object whose .web_app.auth is *auth*."""
    panel = MagicMock()
    panel.web_app = MagicMock()
    panel.web_app.auth = auth
    return panel


def _make_plugin(auth=None, lavalink_client=None, player=None):
    """Create a fake MusicPlugin with the minimum surface area routes need."""
    plugin = MagicMock()
    plugin.name = "music"
    plugin.repeat_modes = {}
    plugin.disconnect_timers = {}

    # Web panel / auth wiring
    if auth is not None:
        plugin.web_panel = _make_web_app(auth)
    else:
        plugin.web_panel = MagicMock()
        plugin.web_panel.web_app = MagicMock()
        plugin.web_panel.web_app.auth = MagicMock()
        plugin.web_panel.web_app.auth.is_configured.return_value = False
        plugin.web_panel.web_app.auth.is_authenticated.return_value = False

    # Lavalink client / player
    if lavalink_client is None:
        lavalink_client = MagicMock()
    if player is None:
        player = MagicMock()
        player.is_connected = True
        player.is_playing = False
        player.paused = False
        player.position = 0
        player.volume = 50
        player.queue = []
        player.current = None
        player.set_volume = AsyncMock()
        player.set_pause = AsyncMock()
        player.play = AsyncMock()
        player.stop = AsyncMock()
        player.skip = AsyncMock()
        player.seek = AsyncMock()
        player.add = MagicMock()

    lavalink_client.player_manager.get.return_value = player
    lavalink_client.player_manager.create.return_value = player
    lavalink_client.get_tracks = AsyncMock()
    plugin.lavalink_client = lavalink_client

    # Plugin helpers
    plugin._save_queue_to_db = AsyncMock()
    plugin._add_to_history = AsyncMock()
    plugin.render_plugin_template = MagicMock(return_value="<html>panel</html>")

    return plugin, player


def _build_app(plugin) -> FastAPI:
    """Register music routes on a fresh FastAPI app."""
    app = FastAPI()
    register_music_routes(app, plugin)
    return app


def _make_request_with_session(app, session_data: dict):
    """Return a TestClient whose underlying app has session middleware wired.

    We use Starlette's SessionMiddleware with a fixed secret so that
    request.session is populated in handlers.
    """
    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(SessionMiddleware, secret_key=TEST_SECRET_KEY)

    client = TestClient(app)

    # Pre-seed the session by hitting a dummy endpoint, or we can just
    # set cookies directly.  The simplest approach: use the client's
    # cookie jar to store a signed session cookie.
    if session_data:
        # Encode session via the middleware's own serializer

        # Create a temporary middleware instance to encode the cookie
        tmp_app = FastAPI()
        tmp_app.add_middleware(SessionMiddleware, secret_key=TEST_SECRET_KEY)

        @tmp_app.get("/_set")
        def _set(request):
            request.session.update(session_data)
            return {"ok": True}

        tmp_client = TestClient(tmp_app)
        resp = tmp_client.get("/_set")
        cookie = resp.headers.get("set-cookie", "")
        if cookie:
            # Extract the session cookie value
            for part in cookie.split(";"):
                part = part.strip()
                if part.startswith("session="):
                    client.cookies["session"] = part[len("session=") :]
                    break

    return client


@pytest.fixture
def authed_client():
    """A TestClient with an authenticated session for GUILD_ID."""
    plugin, player = _make_plugin(
        auth=_make_auth(authenticated=True, guild_ids=[GUILD_ID]),
    )
    app = _build_app(plugin)
    client = _make_request_with_session(
        app,
        {
            "authenticated": True,
            "user": {"id": "111111"},
            "guilds": [{"id": str(GUILD_ID), "name": "Test", "permissions": 0}],
            "access_token": "tok",
        },
    )
    client.plugin = plugin
    client.player = player
    return client


@pytest.fixture
def unauthed_client():
    """A TestClient with no session (unauthenticated)."""
    plugin, player = _make_plugin(
        auth=_make_auth(authenticated=False),
    )
    app = _build_app(plugin)
    client = _make_request_with_session(app, {})
    client.plugin = plugin
    client.player = player
    return client


@pytest.fixture
def wrong_guild_client():
    """A TestClient authenticated but for a different guild."""
    plugin, player = _make_plugin(
        auth=_make_auth(authenticated=True, guild_ids=[OTHER_GUILD_ID]),
    )
    app = _build_app(plugin)
    client = _make_request_with_session(
        app,
        {
            "authenticated": True,
            "user": {"id": "111111"},
            "guilds": [{"id": str(OTHER_GUILD_ID), "name": "Other", "permissions": 0}],
            "access_token": "tok",
        },
    )
    client.plugin = plugin
    client.player = player
    return client


@pytest.fixture
def music_plugin():
    """A bare music plugin mock for command-level tests."""
    plugin, player = _make_plugin(
        auth=_make_auth(authenticated=True, guild_ids=[GUILD_ID]),
    )
    plugin.gateway = MagicMock()
    plugin.gateway.get_me.return_value = MagicMock(id=12345, accent_color=0x00FF00)
    plugin.fetch_user = AsyncMock(return_value=MagicMock(display_name="User", username="user"))
    plugin.fetch_channel = AsyncMock(return_value=MagicMock(name="channel"))
    plugin.get_voice_state = MagicMock(return_value=MagicMock(channel_id=555555))
    plugin.update_voice_state = AsyncMock()
    plugin.create_embed = MagicMock(return_value=MagicMock())
    plugin.smart_respond = AsyncMock()
    plugin.db_session = MagicMock()
    return plugin, player
