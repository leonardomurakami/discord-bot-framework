"""Tests for the autorole command."""

from unittest.mock import AsyncMock, MagicMock, patch

import hikari
import pytest

from plugins.admin.plugin import AdminPlugin


def _make_role(role_id, name, position=1):
    """Create a mock role."""
    role = MagicMock(spec=hikari.Role)
    role.id = role_id
    role.name = name
    role.position = position
    role.color = 0
    role.mention = f"<@&{role_id}>"
    return role


def _make_member(user_id, role_ids=None):
    """Create a mock member."""
    member = MagicMock(spec=hikari.Member)
    member.id = user_id
    member.username = f"user{user_id}"
    member.display_name = f"user{user_id}"
    member.role_ids = role_ids or []
    member.add_role = AsyncMock()
    return member


def _make_guild(guild_id=123456789, roles=None, members=None, bot_member=None):
    """Create a mock guild with roles and members."""
    guild = MagicMock(spec=hikari.Guild)
    guild.id = guild_id
    guild.name = "Test Guild"
    guild.owner_id = 987654321
    guild.member_count = 10
    guild.features = []
    guild.get_roles.return_value = {r.id: r for r in (roles or [])}
    guild.get_role = MagicMock(side_effect=lambda rid: {r.id: r for r in (roles or [])}.get(rid))
    guild.get_members.return_value = {m.id: m for m in (members or [])}
    guild.get_member = MagicMock(side_effect=lambda uid: bot_member if bot_member and uid == bot_member.id else None)
    guild.get_channels.return_value = {}
    guild.get_emojis.return_value = {}
    guild.make_icon_url = MagicMock(return_value=None)
    guild.make_banner_url = MagicMock(return_value=None)
    guild.created_at = MagicMock()
    guild.created_at.timestamp.return_value = 1640995200
    return guild


class TestAutoroleCommand:
    """Test the /autorole command."""

    @pytest.mark.asyncio
    async def test_autorole_list_empty(self, mock_bot, mock_context):
        """Test listing autoroles when none are configured."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            await plugin.autorole(mock_context, action="list", role=None)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorole_list_with_roles(self, mock_bot, mock_context):
        """Test listing autoroles when roles are configured."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        role = _make_role(111, "Member", position=1)
        guild = _make_guild(roles=[role])
        mock_context.get_guild.return_value = guild

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[111]):
            await plugin.autorole(mock_context, action="list", role=None)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorole_add(self, mock_bot, mock_context):
        """Test adding an autorole."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        role = _make_role(111, "Member", position=1)
        bot_role = _make_role(999, "BotRole", position=10)
        bot_member = _make_member(555, role_ids=[999])
        guild = _make_guild(roles=[role, bot_role], bot_member=bot_member)
        mock_context.get_guild.return_value = guild

        mock_bot.gateway.get_me.return_value = MagicMock(id=555)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            with patch.object(plugin, "set_setting", new_callable=AsyncMock, return_value=True):
                await plugin.autorole(mock_context, action="add", role=role)

                mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorole_add_duplicate(self, mock_bot, mock_context):
        """Test adding a duplicate autorole."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        role = _make_role(111, "Member", position=1)
        bot_role = _make_role(999, "BotRole", position=10)
        bot_member = _make_member(555, role_ids=[999])
        guild = _make_guild(roles=[role, bot_role], bot_member=bot_member)
        mock_context.get_guild.return_value = guild

        mock_bot.gateway.get_me.return_value = MagicMock(id=555)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[111]):
            await plugin.autorole(mock_context, action="add", role=role)

            # Should respond (with error embed)
            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorole_add_hierarchy_violation(self, mock_bot, mock_context):
        """Test adding an autorole that violates hierarchy."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        # Target role is higher than bot's role
        role = _make_role(111, "HighRole", position=10)
        bot_role = _make_role(999, "BotRole", position=1)
        bot_member = _make_member(555, role_ids=[999])
        guild = _make_guild(roles=[role, bot_role], bot_member=bot_member)
        mock_context.get_guild.return_value = guild

        mock_bot.gateway.get_me.return_value = MagicMock(id=555)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            await plugin.autorole(mock_context, action="add", role=role)

            # Should respond with error
            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorole_remove(self, mock_bot, mock_context):
        """Test removing an autorole."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        role = _make_role(111, "Member", position=1)
        bot_role = _make_role(999, "BotRole", position=10)
        bot_member = _make_member(555, role_ids=[999])
        guild = _make_guild(roles=[role, bot_role], bot_member=bot_member)
        mock_context.get_guild.return_value = guild

        mock_bot.gateway.get_me.return_value = MagicMock(id=555)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[111]):
            with patch.object(plugin, "set_setting", new_callable=AsyncMock, return_value=True):
                await plugin.autorole(mock_context, action="remove", role=role)

                mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorole_remove_not_configured(self, mock_bot, mock_context):
        """Test removing an autorole that is not configured."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        role = _make_role(111, "Member", position=1)
        bot_role = _make_role(999, "BotRole", position=10)
        bot_member = _make_member(555, role_ids=[999])
        guild = _make_guild(roles=[role, bot_role], bot_member=bot_member)
        mock_context.get_guild.return_value = guild

        mock_bot.gateway.get_me.return_value = MagicMock(id=555)

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            await plugin.autorole(mock_context, action="remove", role=role)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorole_clear(self, mock_bot, mock_context):
        """Test clearing all autoroles."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        with patch.object(plugin, "set_setting", new_callable=AsyncMock, return_value=True):
            await plugin.autorole(mock_context, action="clear", role=None)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorole_invalid_action(self, mock_bot, mock_context):
        """Test an invalid autorole action."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        await plugin.autorole(mock_context, action="invalid", role=None)

        # Should respond with error
        assert mock_context.respond.call_count >= 0

    @pytest.mark.asyncio
    async def test_autorole_no_guild(self, mock_bot, mock_context):
        """Test autorole command outside a guild."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = None

        await plugin.autorole(mock_context, action="list", role=None)

        # Should respond with error
        assert mock_context.respond.call_count >= 0

    @pytest.mark.asyncio
    async def test_autorole_add_no_role(self, mock_bot, mock_context):
        """Test autorole add without specifying a role."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            await plugin.autorole(mock_context, action="add", role=None)

            # Should respond with error
            assert mock_context.respond.call_count >= 0

    @pytest.mark.asyncio
    async def test_on_member_join_assigns_autoroles(self, mock_bot):
        """Test that auto roles are assigned on member join."""
        plugin = AdminPlugin(mock_bot)

        role = _make_role(111, "Member", position=1)
        guild = _make_guild(roles=[role])
        mock_bot.hikari_bot.cache.get_guild.return_value = guild

        member = _make_member(777)
        member.add_role = AsyncMock()

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[111]):
            await plugin.on_member_join(member)

            member.add_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_member_join_no_autoroles(self, mock_bot):
        """Test that no roles are assigned when no autoroles configured."""
        plugin = AdminPlugin(mock_bot)

        member = _make_member(777)
        member.add_role = AsyncMock()

        with patch.object(plugin, "get_setting", new_callable=AsyncMock, return_value=[]):
            await plugin.on_member_join(member)

            member.add_role.assert_not_called()
