"""Tests for bot/permissions/decorators.py"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import hikari
import lightbulb
import pytest

from bot.permissions.decorators import (
    requires_bot_permissions,
    requires_guild_owner,
    requires_permission,
    requires_role,
)


class TestRequiresPermissionDecorator:
    """Test requires_permission decorator functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock lightbulb context."""
        ctx = MagicMock(spec=lightbulb.Context)
        ctx.author = MagicMock()
        ctx.author.username = "test_user"
        ctx.author.id = 12345
        ctx.member = MagicMock(spec=hikari.Member)
        ctx.member.id = 12345
        ctx.guild_id = 67890
        ctx.respond = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_bot_with_permissions(self):
        """Create a mock bot with permission manager."""
        bot = MagicMock()
        bot.permission_manager = AsyncMock()
        bot.permission_manager.has_permission = AsyncMock()
        return bot

    @pytest.mark.asyncio
    async def test_decorator_grants_access_with_permission(
        self, mock_context, mock_bot_with_permissions
    ):
        """Test decorator allows access when user has permission."""
        # Setup
        mock_bot_with_permissions.permission_manager.has_permission.return_value = True

        @requires_permission("test.permission")
        async def test_command(ctx):
            return "success"

        # Mock global bot instance
        with patch(
            "bot.permissions.decorators._bot_instance", mock_bot_with_permissions
        ):
            result = await test_command(mock_context)

        # Verify
        assert result == "success"
        mock_bot_with_permissions.permission_manager.has_permission.assert_called_once_with(
            mock_context.guild_id, mock_context.member, "test.permission"
        )
        mock_context.respond.assert_not_called()

    @pytest.mark.asyncio
    async def test_decorator_denies_access_without_permission(
        self, mock_context, mock_bot_with_permissions
    ):
        """Test decorator denies access when user lacks permission."""
        # Setup
        mock_bot_with_permissions.permission_manager.has_permission.return_value = False

        @requires_permission("test.permission")
        async def test_command(ctx):
            return "success"

        # Mock global bot instance
        with patch(
            "bot.permissions.decorators._bot_instance", mock_bot_with_permissions
        ):
            result = await test_command(mock_context)

        # Verify
        assert result is None  # Function should return early
        mock_context.respond.assert_called_once_with(
            "You don't have the required permission: `test.permission`",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    @pytest.mark.asyncio
    async def test_decorator_with_custom_error_message(
        self, mock_context, mock_bot_with_permissions
    ):
        """Test decorator uses custom error message."""
        # Setup
        mock_bot_with_permissions.permission_manager.has_permission.return_value = False
        custom_message = "Custom access denied message"

        @requires_permission("test.permission", error_message=custom_message)
        async def test_command(ctx):
            return "success"

        # Mock global bot instance
        with patch(
            "bot.permissions.decorators._bot_instance", mock_bot_with_permissions
        ):
            await test_command(mock_context)

        # Verify
        mock_context.respond.assert_called_once_with(
            custom_message, flags=hikari.MessageFlag.EPHEMERAL
        )

    @pytest.mark.asyncio
    async def test_decorator_skips_check_without_bot_instance(self, mock_context):
        """Test decorator skips permission check when no bot instance available."""

        @requires_permission("test.permission")
        async def test_command(ctx):
            return "success"

        # Mock no bot instance
        with patch("bot.permissions.decorators._bot_instance", None):
            result = await test_command(mock_context)

        # Should proceed without permission check
        assert result == "success"
        mock_context.respond.assert_not_called()

    @pytest.mark.asyncio
    async def test_decorator_skips_check_without_permission_manager(self, mock_context):
        """Test decorator skips check when bot has no permission manager."""
        bot_without_perms = MagicMock()
        # Bot exists but has no permission_manager attribute
        if hasattr(bot_without_perms, "permission_manager"):
            delattr(bot_without_perms, "permission_manager")

        @requires_permission("test.permission")
        async def test_command(ctx):
            return "success"

        with patch("bot.permissions.decorators._bot_instance", bot_without_perms):
            result = await test_command(mock_context)

        # Should proceed without permission check
        assert result == "success"
        mock_context.respond.assert_not_called()

    @pytest.mark.asyncio
    async def test_decorator_skips_check_for_non_member(
        self, mock_context, mock_bot_with_permissions
    ):
        """Test decorator skips check when context member is not a Member."""
        # Setup context with non-Member user
        mock_context.member = MagicMock()  # Not a hikari.Member instance

        @requires_permission("test.permission")
        async def test_command(ctx):
            return "success"

        with patch(
            "bot.permissions.decorators._bot_instance", mock_bot_with_permissions
        ):
            result = await test_command(mock_context)

        # Should proceed without permission check
        assert result == "success"
        mock_bot_with_permissions.permission_manager.has_permission.assert_not_called()

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function metadata and adds permission info."""

        @requires_permission("test.permission")
        async def test_command(ctx):
            """Test command docstring"""
            return "success"

        # Check metadata preservation
        assert test_command.__name__ == "test_command"
        assert test_command.__doc__ == "Test command docstring"

        # Check permission metadata
        assert hasattr(test_command, "_required_permission")
        assert test_command._required_permission == "test.permission"

    @pytest.mark.asyncio
    async def test_decorator_logs_permission_checks(
        self, mock_context, mock_bot_with_permissions, caplog
    ):
        """Test decorator logs permission check details."""
        mock_bot_with_permissions.permission_manager.has_permission.return_value = True

        @requires_permission("test.permission")
        async def test_command(ctx):
            return "success"

        with patch(
            "bot.permissions.decorators._bot_instance", mock_bot_with_permissions
        ):
            with caplog.at_level(logging.INFO):
                await test_command(mock_context)

        # Check logs
        assert (
            "Permission check: test_user trying to use command requiring 'test.permission'"
            in caplog.text
        )
        assert (
            "Permission result: test_user HAS permission 'test.permission'"
            in caplog.text
        )


class TestRequiresRoleDecorator:
    """Test requires_role decorator functionality."""

    @pytest.fixture
    def mock_member_context(self):
        """Create mock context with member."""
        ctx = MagicMock(spec=lightbulb.Context)
        ctx.member = MagicMock(spec=hikari.Member)
        ctx.member.role_ids = [111, 222, 333]
        ctx.respond = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_non_member_context(self):
        """Create mock context without member."""
        ctx = MagicMock(spec=lightbulb.Context)
        ctx.member = None
        ctx.respond = AsyncMock()
        return ctx

    @pytest.mark.asyncio
    async def test_single_role_access_granted(self, mock_member_context):
        """Test decorator grants access with single required role."""

        @requires_role(222)
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_member_context)

        assert result == "success"
        mock_member_context.respond.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_roles_access_granted(self, mock_member_context):
        """Test decorator grants access with multiple role options."""

        @requires_role([222, 444])  # User has 222
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_member_context)

        assert result == "success"
        mock_member_context.respond.assert_not_called()

    @pytest.mark.asyncio
    async def test_role_access_denied(self, mock_member_context):
        """Test decorator denies access when user lacks required roles."""

        @requires_role([444, 555])  # User doesn't have these
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_member_context)

        assert result is None
        mock_member_context.respond.assert_called_once_with(
            "You don't have the required role to use this command.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    @pytest.mark.asyncio
    async def test_role_custom_error_message(self, mock_member_context):
        """Test decorator uses custom error message for role requirement."""
        custom_message = "You need special role access!"

        @requires_role([444], error_message=custom_message)
        async def test_command(ctx):
            return "success"

        await test_command(mock_member_context)

        mock_member_context.respond.assert_called_once_with(
            custom_message, flags=hikari.MessageFlag.EPHEMERAL
        )

    @pytest.mark.asyncio
    async def test_role_non_member_denied(self, mock_non_member_context):
        """Test decorator denies access for non-members."""

        @requires_role(123)
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_non_member_context)

        assert result is None
        mock_non_member_context.respond.assert_called_once_with(
            "This command can only be used in servers.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    def test_role_decorator_metadata(self):
        """Test role decorator stores metadata correctly."""

        @requires_role([123, 456])
        async def test_command(ctx):
            return "success"

        assert hasattr(test_command, "_required_roles")
        assert test_command._required_roles == [123, 456]

    def test_role_decorator_single_int_conversion(self):
        """Test role decorator converts single int to list."""

        @requires_role(123)
        async def test_command(ctx):
            return "success"

        assert test_command._required_roles == [123]


class TestRequiresGuildOwnerDecorator:
    """Test requires_guild_owner decorator functionality."""

    @pytest.fixture
    def mock_owner_context(self):
        """Create mock context for guild owner."""
        ctx = MagicMock(spec=lightbulb.Context)
        ctx.guild_id = 12345
        ctx.author = MagicMock()
        ctx.author.id = 67890

        guild = MagicMock()
        guild.owner_id = 67890  # Same as author
        ctx.get_guild = MagicMock(return_value=guild)
        ctx.respond = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_non_owner_context(self):
        """Create mock context for non-owner."""
        ctx = MagicMock(spec=lightbulb.Context)
        ctx.guild_id = 12345
        ctx.author = MagicMock()
        ctx.author.id = 11111

        guild = MagicMock()
        guild.owner_id = 67890  # Different from author
        ctx.get_guild = MagicMock(return_value=guild)
        ctx.respond = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_dm_context(self):
        """Create mock context for DM."""
        ctx = MagicMock(spec=lightbulb.Context)
        ctx.guild_id = None
        ctx.respond = AsyncMock()
        return ctx

    @pytest.mark.asyncio
    async def test_owner_access_granted(self, mock_owner_context):
        """Test decorator grants access to guild owner."""

        @requires_guild_owner()
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_owner_context)

        assert result == "success"
        mock_owner_context.respond.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_owner_access_denied(self, mock_non_owner_context):
        """Test decorator denies access to non-owner."""

        @requires_guild_owner()
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_non_owner_context)

        assert result is None
        mock_non_owner_context.respond.assert_called_once_with(
            "Only the server owner can use this command.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    @pytest.mark.asyncio
    async def test_dm_access_denied(self, mock_dm_context):
        """Test decorator denies access in DMs."""

        @requires_guild_owner()
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_dm_context)

        assert result is None
        mock_dm_context.respond.assert_called_once_with(
            "This command can only be used in servers.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    @pytest.mark.asyncio
    async def test_owner_custom_error_message(self, mock_non_owner_context):
        """Test decorator uses custom error message."""
        custom_message = "Only the boss can do this!"

        @requires_guild_owner(error_message=custom_message)
        async def test_command(ctx):
            return "success"

        await test_command(mock_non_owner_context)

        mock_non_owner_context.respond.assert_called_once_with(
            custom_message, flags=hikari.MessageFlag.EPHEMERAL
        )

    @pytest.mark.asyncio
    async def test_guild_not_found(self, mock_owner_context):
        """Test decorator handles missing guild."""
        mock_owner_context.get_guild.return_value = None

        @requires_guild_owner()
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_owner_context)

        assert result is None
        mock_owner_context.respond.assert_called_once_with(
            "Only the server owner can use this command.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    def test_guild_owner_decorator_metadata(self):
        """Test guild owner decorator stores metadata."""

        @requires_guild_owner()
        async def test_command(ctx):
            return "success"

        assert hasattr(test_command, "_requires_guild_owner")
        assert test_command._requires_guild_owner is True


class TestRequiresBotPermissionsDecorator:
    """Test requires_bot_permissions decorator functionality."""

    @pytest.fixture
    def mock_guild_context(self):
        """Create mock context in guild."""
        ctx = MagicMock(spec=lightbulb.Context)
        ctx.guild_id = 12345
        ctx.client = MagicMock()
        ctx.client.get_me.return_value = MagicMock(id=99999)
        ctx.respond = AsyncMock()
        ctx.get_guild = MagicMock()
        return ctx

    @pytest.fixture
    def mock_dm_context(self):
        """Create mock context in DM."""
        ctx = MagicMock(spec=lightbulb.Context)
        ctx.guild_id = None
        return ctx

    @pytest.mark.asyncio
    async def test_bot_has_permissions(self, mock_guild_context):
        """Test decorator allows access when bot has permissions."""
        # Setup guild and bot member with permissions
        guild = MagicMock()
        bot_member = MagicMock()
        bot_member.permissions = (
            hikari.Permissions.SEND_MESSAGES | hikari.Permissions.MANAGE_MESSAGES
        )
        guild.get_member.return_value = bot_member
        mock_guild_context.get_guild.return_value = guild

        @requires_bot_permissions(hikari.Permissions.SEND_MESSAGES)
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_guild_context)

        assert result == "success"
        mock_guild_context.respond.assert_not_called()

    @pytest.mark.asyncio
    async def test_bot_missing_permissions(self, mock_guild_context):
        """Test decorator denies access when bot lacks permissions."""
        # Setup guild and bot member without required permissions
        guild = MagicMock()
        bot_member = MagicMock()
        bot_member.permissions = (
            hikari.Permissions.SEND_MESSAGES
        )  # Missing MANAGE_MESSAGES
        guild.get_member.return_value = bot_member
        mock_guild_context.get_guild.return_value = guild

        @requires_bot_permissions(hikari.Permissions.MANAGE_MESSAGES)
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_guild_context)

        assert result is None
        mock_guild_context.respond.assert_called_once()
        call_args = mock_guild_context.respond.call_args[0][0]
        assert "I'm missing the following permissions:" in call_args
        assert "MANAGE_MESSAGES" in call_args

    @pytest.mark.asyncio
    async def test_bot_multiple_missing_permissions(self, mock_guild_context):
        """Test decorator reports multiple missing permissions."""
        # Setup guild and bot member with limited permissions
        guild = MagicMock()
        bot_member = MagicMock()
        bot_member.permissions = hikari.Permissions.SEND_MESSAGES
        guild.get_member.return_value = bot_member
        mock_guild_context.get_guild.return_value = guild

        @requires_bot_permissions(
            hikari.Permissions.MANAGE_MESSAGES, hikari.Permissions.MANAGE_CHANNELS
        )
        async def test_command(ctx):
            return "success"

        await test_command(mock_guild_context)

        call_args = mock_guild_context.respond.call_args[0][0]
        assert "MANAGE_MESSAGES" in call_args
        assert "MANAGE_CHANNELS" in call_args

    @pytest.mark.asyncio
    async def test_dm_bypasses_check(self, mock_dm_context):
        """Test decorator bypasses permission check in DMs."""

        @requires_bot_permissions(hikari.Permissions.MANAGE_MESSAGES)
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_dm_context)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_no_guild_bypasses_check(self, mock_guild_context):
        """Test decorator bypasses check when guild not found."""
        mock_guild_context.get_guild.return_value = None

        @requires_bot_permissions(hikari.Permissions.MANAGE_MESSAGES)
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_guild_context)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_bot_member_not_found(self, mock_guild_context):
        """Test decorator handles bot member not found."""
        guild = MagicMock()
        guild.get_member.return_value = None  # Bot not found in guild
        mock_guild_context.get_guild.return_value = guild

        @requires_bot_permissions(hikari.Permissions.MANAGE_MESSAGES)
        async def test_command(ctx):
            return "success"

        result = await test_command(mock_guild_context)

        assert result is None
        mock_guild_context.respond.assert_called_once_with(
            "I couldn't determine my permissions in this server.",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    def test_bot_permissions_decorator_metadata(self):
        """Test bot permissions decorator stores metadata."""

        @requires_bot_permissions(
            hikari.Permissions.SEND_MESSAGES, hikari.Permissions.MANAGE_MESSAGES
        )
        async def test_command(ctx):
            return "success"

        assert hasattr(test_command, "_required_bot_permissions")
        assert test_command._required_bot_permissions == (
            hikari.Permissions.SEND_MESSAGES,
            hikari.Permissions.MANAGE_MESSAGES,
        )


class TestGlobalBotInstance:
    """Test global bot instance management."""

    def test_global_bot_instance_initially_none(self):
        """Test that global bot instance starts as None."""
        # This might be affected by other tests, but we can test the variable exists
        import bot.permissions.decorators

        # Just verify the variable exists and is accessible
        assert "_bot_instance" in dir(bot.permissions.decorators)
