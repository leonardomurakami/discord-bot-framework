"""Tests for admin web routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import hikari
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from plugins.admin.plugin import AdminPlugin
from plugins.admin.web.routes import esc_html, register_admin_routes


def _make_mock_auth(authenticated=True, guilds=None):
    """Create a mock DiscordAuth."""
    auth = MagicMock()
    auth.is_authenticated.return_value = authenticated
    user_data = {
        "user": {"id": "111", "username": "testuser"},
        "guilds": guilds or [{"id": "123456789", "permissions": 0x8, "name": "Test Guild"}],
    }
    auth.get_current_user.return_value = user_data
    return auth


def _make_mock_web_panel(auth=None):
    """Create a mock web panel manager."""
    web_panel = MagicMock()
    web_app = MagicMock()
    web_app.auth = auth or _make_mock_auth()
    web_panel.web_app = web_app
    return web_panel


def _make_plugin(mock_bot, auth=None):
    """Create an AdminPlugin with mocked web panel."""
    plugin = AdminPlugin(mock_bot)
    plugin.web_panel = _make_mock_web_panel(auth)
    return plugin


def _make_app(plugin):
    """Create a FastAPI app with admin routes registered."""
    app = FastAPI()
    register_admin_routes(app, plugin)
    return app


def _make_role(role_id, name, position=1):
    """Create a mock role."""
    role = MagicMock(spec=hikari.Role)
    role.id = role_id
    role.name = name
    role.position = position
    role.color = 0
    return role


def _make_guild(guild_id=123456789, roles=None, members=None):
    """Create a mock guild."""
    guild = MagicMock(spec=hikari.Guild)
    guild.id = guild_id
    guild.name = "Test Guild"
    guild.owner_id = 987654321
    guild.member_count = 100
    guild.features = ["COMMUNITY"]
    guild.created_at = MagicMock()
    guild.created_at.isoformat.return_value = "2022-01-01T00:00:00"
    guild.created_at.timestamp.return_value = 1640995200
    guild.make_icon_url = MagicMock(return_value="https://example.com/icon.png")
    guild.make_banner_url = MagicMock(return_value=None)
    guild.get_roles.return_value = {r.id: r for r in (roles or [])}
    guild.get_role = MagicMock(side_effect=lambda rid: {r.id: r for r in (roles or [])}.get(rid))
    guild.get_members.return_value = {m.id: m for m in (members or [])}
    guild.get_channels.return_value = {}
    guild.get_emojis.return_value = {}
    return guild


class TestEscHtml:
    """Test the esc_html helper."""

    def test_esc_html_escapes_quotes(self):
        """Test that single quotes are escaped."""
        result = esc_html("it's a test")
        assert "&#x27;" in result or "&#39;" in result
        assert "'" not in result

    def test_esc_html_escapes_angle_brackets(self):
        """Test that angle brackets are escaped."""
        result = esc_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_esc_html_escapes_ampersand(self):
        """Test that ampersands are escaped."""
        result = esc_html("a & b")
        assert "&amp;" in result

    def test_esc_html_plain_text(self):
        """Test that plain text is unchanged."""
        result = esc_html("hello world")
        assert result == "hello world"


class TestPrefixRoutes:
    """Test prefix web routes."""

    def test_get_prefix_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/api/guild/123456789/prefix")
        assert response.status_code == 401

    def test_get_prefix_authenticated(self, mock_bot):
        """Test getting the current prefix."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch.object(plugin, "get_guild_prefix", new_callable=AsyncMock, return_value="!"):
            response = client.get("/plugin/admin/api/guild/123456789/prefix")
            assert response.status_code == 200
            data = response.json()
            assert data["prefix"] == "!"

    def test_post_prefix_valid(self, mock_bot):
        """Test setting a valid prefix."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_guild = MagicMock()
        mock_guild.prefix = "!"
        mock_result.scalar_one_or_none.return_value = mock_guild
        mock_session.execute.return_value = mock_result

        with patch("plugins.admin.web.routes.ensure_guild_exists", new_callable=AsyncMock, return_value=True):
            with patch("plugins.admin.web.routes.db_manager") as mock_db:
                mock_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_db.session.return_value.__aexit__ = AsyncMock(return_value=None)
                response = client.post(
                    "/plugin/admin/api/guild/123456789/prefix",
                    data={"new_prefix": "?"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["prefix"] == "?"

    def test_post_prefix_too_long(self, mock_bot):
        """Test rejecting a prefix that is too long."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.post(
            "/plugin/admin/api/guild/123456789/prefix",
            data={"new_prefix": "!!!!!!"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_post_prefix_empty(self, mock_bot):
        """Test rejecting an empty prefix."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.post(
            "/plugin/admin/api/guild/123456789/prefix",
            data={"new_prefix": "   "},
        )
        assert response.status_code == 400

    def test_post_prefix_disallowed_chars(self, mock_bot):
        """Test rejecting a prefix with disallowed characters."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.post(
            "/plugin/admin/api/guild/123456789/prefix",
            data={"new_prefix": "!'`"},
        )
        assert response.status_code == 400


class TestAutoroleRoutes:
    """Test autorole web routes."""

    def test_get_autoroles_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/api/guild/123456789/autoroles")
        assert response.status_code == 401

    def test_get_autoroles_empty(self, mock_bot):
        """Test getting autoroles when none are configured."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            response = client.get("/plugin/admin/api/guild/123456789/autoroles")
            assert response.status_code == 200
            data = response.json()
            assert data["autoroles"] == []

    def test_get_autoroles_with_roles(self, mock_bot):
        """Test getting autoroles with configured roles."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        role = _make_role(111, "Member", position=1)
        guild = _make_guild(roles=[role])
        mock_bot.hikari_bot.cache.get_guild.return_value = guild

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[111]):
            response = client.get("/plugin/admin/api/guild/123456789/autoroles")
            assert response.status_code == 200
            data = response.json()
            assert len(data["autoroles"]) == 1
            assert data["autoroles"][0]["name"] == "Member"

    def test_post_autorole_add(self, mock_bot):
        """Test adding an autorole."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        role = _make_role(111, "Member", position=1)
        bot_role = _make_role(999, "BotRole", position=10)
        bot_member = MagicMock()
        bot_member.id = 555
        bot_member.role_ids = [999]
        guild = _make_guild(roles=[role, bot_role])
        guild.get_member.return_value = bot_member
        mock_bot.hikari_bot.cache.get_guild.return_value = guild
        mock_bot.hikari_bot.get_me.return_value = MagicMock(id=555)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            with patch.object(plugin, "set_setting", new_callable=AsyncMock, return_value=True):
                response = client.post(
                    "/plugin/admin/api/guild/123456789/autoroles",
                    data={"role_id": "111"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_post_autorole_add_duplicate(self, mock_bot):
        """Test adding a duplicate autorole."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        role = _make_role(111, "Member", position=1)
        bot_role = _make_role(999, "BotRole", position=10)
        bot_member = MagicMock()
        bot_member.id = 555
        bot_member.role_ids = [999]
        guild = _make_guild(roles=[role, bot_role])
        guild.get_member.return_value = bot_member
        mock_bot.hikari_bot.cache.get_guild.return_value = guild
        mock_bot.hikari_bot.get_me.return_value = MagicMock(id=555)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[111]):
            response = client.post(
                "/plugin/admin/api/guild/123456789/autoroles",
                data={"role_id": "111"},
            )
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False

    def test_post_autorole_add_hierarchy_violation(self, mock_bot):
        """Test adding an autorole that violates hierarchy."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        role = _make_role(111, "HighRole", position=10)
        bot_role = _make_role(999, "BotRole", position=1)
        bot_member = MagicMock()
        bot_member.id = 555
        bot_member.role_ids = [999]
        guild = _make_guild(roles=[role, bot_role])
        guild.get_member.return_value = bot_member
        mock_bot.hikari_bot.cache.get_guild.return_value = guild
        mock_bot.hikari_bot.get_me.return_value = MagicMock(id=555)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            response = client.post(
                "/plugin/admin/api/guild/123456789/autoroles",
                data={"role_id": "111"},
            )
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False

    def test_delete_autorole(self, mock_bot):
        """Test removing an autorole."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[111]):
            with patch.object(plugin, "set_setting", new_callable=AsyncMock, return_value=True):
                response = client.delete("/plugin/admin/api/guild/123456789/autoroles/111")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_delete_autorole_not_configured(self, mock_bot):
        """Test removing an autorole that is not configured."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            response = client.delete("/plugin/admin/api/guild/123456789/autoroles/111")
            assert response.status_code == 400


class TestBotInfoRoute:
    """Test bot info web route."""

    def test_bot_info_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/api/bot-info")
        assert response.status_code == 401

    def test_bot_info_authenticated(self, mock_bot):
        """Test getting bot info."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_overview = MagicMock()
        mock_overview.user = MagicMock()
        mock_overview.user.username = "TestBot"
        mock_overview.user.display_name = "TestBot"
        mock_overview.user.display_avatar_url = "https://example.com/avatar.png"
        mock_overview.user.created_at = None
        mock_overview.guild_count = 5
        mock_overview.plugin_count = 3
        mock_overview.database_connected = True

        with patch.object(plugin.bot, "get_bot_overview", new_callable=AsyncMock, return_value=mock_overview):
            response = client.get("/plugin/admin/api/bot-info")
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "TestBot"
            assert data["guild_count"] == 5
            assert data["plugin_count"] == 3
            assert data["database_connected"] is True


class TestServerInfoRoute:
    """Test server info web route."""

    def test_server_info_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/api/guild/123456789/server-info")
        assert response.status_code == 401

    def test_server_info_guild_not_found(self, mock_bot):
        """Test server info when guild is not in cache."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_bot.hikari_bot.cache.get_guild.return_value = None

        response = client.get("/plugin/admin/api/guild/123456789/server-info")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False

    def test_server_info_authenticated(self, mock_bot):
        """Test getting server info."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        guild = _make_guild()
        mock_bot.hikari_bot.cache.get_guild.return_value = guild

        mock_summary = MagicMock()
        mock_summary.member_count = 100
        mock_summary.channel_count = 5
        mock_summary.text_channels = 3
        mock_summary.voice_channels = 1
        mock_summary.category_channels = 1
        mock_summary.role_count = 10
        mock_summary.emoji_count = 5

        with patch.object(plugin.bot, "summarise_guild", return_value=mock_summary):
            response = client.get("/plugin/admin/api/guild/123456789/server-info")
            assert response.status_code == 200
            data = response.json()
            assert data["available"] is True
            assert data["name"] == "Test Guild"
            assert data["member_count"] == 100


class TestStatusRoute:
    """Test status web route."""

    def test_status_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/api/status")
        assert response.status_code == 401

    def test_status_with_psutil(self, mock_bot):
        """Test getting status with psutil available."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_bot.hikari_bot.cache.get_guilds_view.return_value = {1: MagicMock()}
        mock_bot.hikari_bot.heartbeat_latency = 0.05

        response = client.get("/plugin/admin/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["guild_count"] == 1
        assert data["latency_ms"] is not None
        # psutil is installed as a dependency, so it should be available
        assert data.get("psutil_available", False) is True

    def test_status_without_psutil(self, mock_bot):
        """Test getting status when psutil is not available."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_bot.hikari_bot.cache.get_guilds_view.return_value = {1: MagicMock()}
        mock_bot.hikari_bot.heartbeat_latency = 0.05

        original_import = __import__

        def import_side_effect(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("No module named 'psutil'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            response = client.get("/plugin/admin/api/status")
            assert response.status_code == 200
            data = response.json()
            assert data["psutil_available"] is False
            assert data["guild_count"] == 1


class TestRolesRoute:
    """Test the guild roles endpoint."""

    def test_get_roles_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/api/guild/123456789/roles")
        assert response.status_code == 401

    def test_get_roles_authenticated(self, mock_bot):
        """Test getting guild roles."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        role = _make_role(111, "TestRole", position=5)
        guild = _make_guild(roles=[role])
        mock_bot.hikari_bot.cache.get_guild.return_value = guild

        response = client.get("/plugin/admin/api/guild/123456789/roles")
        assert response.status_code == 200
        assert "TestRole" in response.text

    def test_get_roles_guild_not_found(self, mock_bot):
        """Test getting roles when guild is not in cache."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_bot.hikari_bot.cache.get_guild.return_value = None

        response = client.get("/plugin/admin/api/guild/123456789/roles")
        assert response.status_code == 200
        assert "not found" in response.text.lower() or "error" in response.text.lower()


class TestMembersRoute:
    """Test the guild members endpoint."""

    def test_get_members_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/api/guild/123456789/members")
        assert response.status_code == 401

    def test_get_members_authenticated(self, mock_bot):
        """Test getting guild members."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        member = MagicMock()
        member.id = 777
        member.username = "testuser"
        member.display_name = "Test User"
        member.make_avatar_url.return_value = "https://example.com/avatar.png"

        guild = _make_guild(members=[member])
        mock_bot.hikari_bot.cache.get_guild.return_value = guild

        response = client.get("/plugin/admin/api/guild/123456789/members")
        assert response.status_code == 200
        assert "Test User" in response.text

    def test_get_members_guild_not_found(self, mock_bot):
        """Test getting members when guild is not in cache."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_bot.hikari_bot.cache.get_guild.return_value = None

        response = client.get("/plugin/admin/api/guild/123456789/members")
        assert response.status_code == 200
        assert "not found" in response.text.lower() or "error" in response.text.lower()


class TestCheckAccessRoute:
    """Test the check-access endpoint."""

    def test_check_access_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/check-access/123456789")
        assert response.status_code == 401

    def test_check_access_admin(self, mock_bot):
        """Test check-access for an admin user."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_bot.hikari_bot.cache.get_guild.return_value = None

        response = client.get("/plugin/admin/check-access/123456789")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_check_access_no_permission(self, mock_bot):
        """Test check-access for a user without admin permission."""
        guilds = [{"id": "123456789", "permissions": 0, "name": "Test Guild"}]
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(guilds=guilds))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/check-access/123456789")
        assert response.status_code == 403


class TestAllPermissionsRoute:
    """Test the all permissions endpoint."""

    def test_permissions_unauthenticated(self, mock_bot):
        """Test that unauthenticated requests get 401."""
        plugin = _make_plugin(mock_bot, auth=_make_mock_auth(authenticated=False))
        app = _make_app(plugin)
        client = TestClient(app)

        response = client.get("/plugin/admin/api/permissions")
        assert response.status_code == 401

    def test_permissions_authenticated(self, mock_bot):
        """Test getting all permissions."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_perm = MagicMock()
        mock_perm.id = 1
        mock_perm.node = "admin.manage"
        mock_perm.description = "Manage admin"
        mock_perm.category = "admin"

        with patch("plugins.admin.web.routes.get_all_permissions", new_callable=AsyncMock, return_value=[mock_perm]):
            response = client.get("/plugin/admin/api/permissions")
            assert response.status_code == 200
            data = response.json()
            assert len(data["permissions"]) == 1
            assert data["permissions"][0]["node"] == "admin.manage"


class TestRolePermissionRoutes:
    """Test role permission grant/revoke endpoints."""

    def test_get_role_permissions(self, mock_bot):
        """Test getting role permissions."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch("plugins.admin.web.routes.get_role_granted_permissions", new_callable=AsyncMock, return_value=["admin.manage"]):
            response = client.get("/plugin/admin/api/guild/123456789/role/111/permissions")
            assert response.status_code == 200
            data = response.json()
            assert "admin.manage" in data["permissions"]

    def test_grant_role_permission(self, mock_bot):
        """Test granting a role permission."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch("plugins.admin.web.routes.ensure_guild_exists", new_callable=AsyncMock, return_value=True):
            mock_bot.permission_manager.grant_permission = AsyncMock(return_value=(True, ["admin.manage"], []))
            response = client.post(
                "/plugin/admin/api/guild/123456789/role/111/permissions/grant",
                data={"permission_node": "admin.manage"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_revoke_role_permission(self, mock_bot):
        """Test revoking a role permission."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch("plugins.admin.web.routes.ensure_guild_exists", new_callable=AsyncMock, return_value=True):
            mock_bot.permission_manager.revoke_permission = AsyncMock(return_value=(True, ["admin.manage"], []))
            response = client.post(
                "/plugin/admin/api/guild/123456789/role/111/permissions/revoke",
                data={"permission_node": "admin.manage"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestUserPermissionRoutes:
    """Test user permission grant/revoke endpoints."""

    def test_get_user_permissions(self, mock_bot):
        """Test getting user permissions."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        mock_bot.permission_manager.get_user_direct_permissions = AsyncMock(return_value=["admin.manage"])
        response = client.get("/plugin/admin/api/guild/123456789/user/111/permissions")
        assert response.status_code == 200
        data = response.json()
        assert "admin.manage" in data["permissions"]

    def test_grant_user_permission(self, mock_bot):
        """Test granting a user permission."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch("plugins.admin.web.routes.ensure_guild_exists", new_callable=AsyncMock, return_value=True):
            mock_bot.permission_manager.grant_user_permission = AsyncMock(return_value=(True, ["admin.manage"], []))
            response = client.post(
                "/plugin/admin/api/guild/123456789/user/111/permissions/grant",
                data={"permission_node": "admin.manage"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_revoke_user_permission(self, mock_bot):
        """Test revoking a user permission."""
        plugin = _make_plugin(mock_bot)
        app = _make_app(plugin)
        client = TestClient(app)

        with patch("plugins.admin.web.routes.ensure_guild_exists", new_callable=AsyncMock, return_value=True):
            mock_bot.permission_manager.revoke_user_permission = AsyncMock(return_value=(True, ["admin.manage"], []))
            response = client.post(
                "/plugin/admin/api/guild/123456789/user/111/permissions/revoke",
                data={"permission_node": "admin.manage"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestEnsureGuildExists:
    """Test the ensure_guild_exists helper."""

    @pytest.mark.asyncio
    async def test_ensure_guild_exists_creates_new(self, mock_bot):
        """Test that ensure_guild_exists creates a new guild record."""
        from plugins.admin.web.routes import ensure_guild_exists

        plugin = _make_plugin(mock_bot)
        mock_bot.hikari_bot.cache.get_guild.return_value = None

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch("plugins.admin.web.routes.db_manager") as mock_db:
            mock_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.session.return_value.__aexit__ = AsyncMock(return_value=None)
            result = await ensure_guild_exists(123456789, plugin)
            assert result is True

    @pytest.mark.asyncio
    async def test_ensure_guild_exists_already_exists(self, mock_bot):
        """Test that ensure_guild_exists returns True when guild exists."""
        from plugins.admin.web.routes import ensure_guild_exists

        plugin = _make_plugin(mock_bot)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_guild = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_guild
        mock_session.execute.return_value = mock_result

        with patch("plugins.admin.web.routes.db_manager") as mock_db:
            mock_db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.session.return_value.__aexit__ = AsyncMock(return_value=None)
            result = await ensure_guild_exists(123456789, plugin)
            assert result is True
