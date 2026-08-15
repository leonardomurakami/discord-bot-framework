"""Tests for admin Miru pagination views."""

from unittest.mock import AsyncMock, MagicMock

import hikari
import miru
import pytest

from plugins.admin.plugin import AdminPlugin
from plugins.admin.views import PermissionsPaginationView, RolePermissionsPaginationView


def _make_permission(node, description, category="general"):
    """Create a mock permission object."""
    perm = MagicMock()
    perm.node = node
    perm.description = description
    perm.category = category
    return perm


def _make_role(role_id, name, position=1):
    """Create a mock role."""
    role = MagicMock(spec=hikari.Role)
    role.id = role_id
    role.name = name
    role.position = position
    role.color = 0
    return role


class TestPermissionsPaginationView:
    """Test the PermissionsPaginationView."""

    def test_view_creation_with_permissions(self, mock_bot):
        """Test creating a pagination view with permissions."""
        plugin = AdminPlugin(mock_bot)
        permissions = [
            _make_permission("admin.manage", "Manage admin", "admin"),
            _make_permission("admin.config", "Manage config", "admin"),
            _make_permission("moderation.kick", "Kick members", "moderation"),
        ]

        view = PermissionsPaginationView(plugin, permissions, page_size=2)

        assert view.total_pages == 2
        assert view.current_page == 0

    def test_view_creation_empty(self, mock_bot):
        """Test creating a pagination view with no permissions."""
        plugin = AdminPlugin(mock_bot)

        view = PermissionsPaginationView(plugin, [], page_size=10)

        assert view.total_pages == 1
        assert view.current_page == 0

    def test_get_current_page_embed_first_page(self, mock_bot):
        """Test getting the embed for the first page."""
        plugin = AdminPlugin(mock_bot)
        permissions = [
            _make_permission("admin.manage", "Manage admin", "admin"),
            _make_permission("admin.config", "Manage config", "admin"),
        ]

        view = PermissionsPaginationView(plugin, permissions, page_size=1)
        embed = view.get_current_page_embed()

        assert embed is not None

    def test_get_current_page_embed_empty(self, mock_bot):
        """Test getting the embed when there are no permissions."""
        plugin = AdminPlugin(mock_bot)

        view = PermissionsPaginationView(plugin, [], page_size=10)
        embed = view.get_current_page_embed()

        assert embed is not None

    def test_get_current_page_embed_last_page(self, mock_bot):
        """Test getting the embed for the last page."""
        plugin = AdminPlugin(mock_bot)
        permissions = [
            _make_permission("admin.manage", "Manage admin", "admin"),
            _make_permission("admin.config", "Manage config", "admin"),
            _make_permission("moderation.kick", "Kick members", "moderation"),
        ]

        view = PermissionsPaginationView(plugin, permissions, page_size=2, initial_page=1)
        embed = view.get_current_page_embed()

        assert embed is not None

    def test_button_states_first_page(self, mock_bot):
        """Test button states on the first page."""
        plugin = AdminPlugin(mock_bot)
        permissions = [_make_permission(f"perm.{i}", f"Permission {i}") for i in range(25)]

        view = PermissionsPaginationView(plugin, permissions, page_size=10)

        # On first page, prev should be disabled
        for item in view.children:
            if isinstance(item, miru.Button):
                if item.custom_id == "permissions_prev_page":
                    assert item.disabled is True
                if item.custom_id == "permissions_next_page":
                    assert item.disabled is False

    def test_button_states_last_page(self, mock_bot):
        """Test button states on the last page."""
        plugin = AdminPlugin(mock_bot)
        permissions = [_make_permission(f"perm.{i}", f"Permission {i}") for i in range(25)]

        view = PermissionsPaginationView(plugin, permissions, page_size=10, initial_page=2)
        view._update_button_states()

        # On last page, next should be disabled
        for item in view.children:
            if isinstance(item, miru.Button):
                if item.custom_id == "permissions_prev_page":
                    assert item.disabled is False
                if item.custom_id == "permissions_next_page":
                    assert item.disabled is True

    @pytest.mark.asyncio
    async def test_on_next_page(self, mock_bot):
        """Test navigating to the next page."""
        plugin = AdminPlugin(mock_bot)
        permissions = [_make_permission(f"perm.{i}", f"Permission {i}") for i in range(25)]

        view = PermissionsPaginationView(plugin, permissions, page_size=10)
        assert view.current_page == 0

        mock_ctx = MagicMock()
        mock_ctx.edit_response = AsyncMock()

        await view.on_next_page(mock_ctx)

        assert view.current_page == 1
        mock_ctx.edit_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_previous_page(self, mock_bot):
        """Test navigating to the previous page."""
        plugin = AdminPlugin(mock_bot)
        permissions = [_make_permission(f"perm.{i}", f"Permission {i}") for i in range(25)]

        view = PermissionsPaginationView(plugin, permissions, page_size=10, initial_page=1)
        assert view.current_page == 1

        mock_ctx = MagicMock()
        mock_ctx.edit_response = AsyncMock()

        await view.on_previous_page(mock_ctx)

        assert view.current_page == 0
        mock_ctx.edit_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_previous_page_boundary(self, mock_bot):
        """Test that previous page does nothing on the first page."""
        plugin = AdminPlugin(mock_bot)
        permissions = [_make_permission(f"perm.{i}", f"Permission {i}") for i in range(25)]

        view = PermissionsPaginationView(plugin, permissions, page_size=10)
        assert view.current_page == 0

        mock_ctx = MagicMock()
        mock_ctx.respond = AsyncMock()

        await view.on_previous_page(mock_ctx)

        assert view.current_page == 0
        mock_ctx.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_next_page_boundary(self, mock_bot):
        """Test that next page does nothing on the last page."""
        plugin = AdminPlugin(mock_bot)
        permissions = [_make_permission(f"perm.{i}", f"Permission {i}") for i in range(25)]

        view = PermissionsPaginationView(plugin, permissions, page_size=10, initial_page=2)
        assert view.current_page == 2

        mock_ctx = MagicMock()
        mock_ctx.respond = AsyncMock()

        await view.on_next_page(mock_ctx)

        assert view.current_page == 2
        mock_ctx.respond.assert_called_once()


class TestRolePermissionsPaginationView:
    """Test the RolePermissionsPaginationView."""

    def test_view_creation_with_permissions(self, mock_bot):
        """Test creating a role permissions pagination view."""
        plugin = AdminPlugin(mock_bot)
        role = _make_role(111, "TestRole")
        permissions = ["admin.manage", "admin.config", "moderation.kick"]

        view = RolePermissionsPaginationView(plugin, role, permissions, page_size=2)

        assert view.total_pages == 2
        assert view.current_page == 0
        assert view.role.name == "TestRole"

    def test_view_creation_empty(self, mock_bot):
        """Test creating a role permissions view with no permissions."""
        plugin = AdminPlugin(mock_bot)
        role = _make_role(111, "TestRole")

        view = RolePermissionsPaginationView(plugin, role, [], page_size=10)

        assert view.total_pages == 1

    def test_get_current_page_embed_first_page(self, mock_bot):
        """Test getting the embed for the first page."""
        plugin = AdminPlugin(mock_bot)
        role = _make_role(111, "TestRole")
        permissions = ["admin.manage", "admin.config"]

        view = RolePermissionsPaginationView(plugin, role, permissions, page_size=1)
        embed = view.get_current_page_embed()

        assert embed is not None

    def test_get_current_page_embed_empty(self, mock_bot):
        """Test getting the embed when there are no permissions."""
        plugin = AdminPlugin(mock_bot)
        role = _make_role(111, "TestRole")

        view = RolePermissionsPaginationView(plugin, role, [], page_size=10)
        embed = view.get_current_page_embed()

        assert embed is not None

    @pytest.mark.asyncio
    async def test_on_next_page(self, mock_bot):
        """Test navigating to the next page."""
        plugin = AdminPlugin(mock_bot)
        role = _make_role(111, "TestRole")
        permissions = ["admin.manage", "admin.config", "moderation.kick"]

        view = RolePermissionsPaginationView(plugin, role, permissions, page_size=1)
        assert view.current_page == 0

        mock_ctx = MagicMock()
        mock_ctx.edit_response = AsyncMock()

        await view.on_next_page(mock_ctx)

        assert view.current_page == 1
        mock_ctx.edit_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_previous_page(self, mock_bot):
        """Test navigating to the previous page."""
        plugin = AdminPlugin(mock_bot)
        role = _make_role(111, "TestRole")
        permissions = ["admin.manage", "admin.config", "moderation.kick"]

        view = RolePermissionsPaginationView(plugin, role, permissions, page_size=1, initial_page=2)
        assert view.current_page == 2

        mock_ctx = MagicMock()
        mock_ctx.edit_response = AsyncMock()

        await view.on_previous_page(mock_ctx)

        assert view.current_page == 1
        mock_ctx.edit_response.assert_called_once()
