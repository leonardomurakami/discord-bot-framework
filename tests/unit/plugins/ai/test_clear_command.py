"""Tests for the AI plugin `clearai` command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.ai.commands.clear import _handle_clear


def _build_plugin() -> MagicMock:
    plugin = MagicMock()
    plugin.db_session = MagicMock()
    plugin.respond_success = AsyncMock()
    plugin.respond_error = AsyncMock()
    return plugin


@pytest.fixture
def patched_clear_history():
    with patch("plugins.ai.commands.clear.clear_history", new_callable=AsyncMock) as mock:
        yield mock


class TestClearAICommand:
    @pytest.mark.asyncio
    async def test_clear_with_existing_history(self, mock_context, patched_clear_history):
        from tests.conftest import AsyncContextManager

        patched_clear_history.return_value = 5
        plugin = _build_plugin()
        plugin.db_session.return_value = AsyncContextManager(MagicMock())

        await _handle_clear(plugin, mock_context)

        patched_clear_history.assert_awaited_once()
        plugin.respond_success.assert_awaited_once()
        args, _ = plugin.respond_success.call_args
        assert "5" in args[1]

    @pytest.mark.asyncio
    async def test_clear_with_no_history(self, mock_context, patched_clear_history):
        from tests.conftest import AsyncContextManager

        patched_clear_history.return_value = 0
        plugin = _build_plugin()
        plugin.db_session.return_value = AsyncContextManager(MagicMock())

        await _handle_clear(plugin, mock_context)

        plugin.respond_success.assert_awaited_once()
        args, _ = plugin.respond_success.call_args
        assert "no" in args[1].lower() or "no history" in args[1].lower()

    @pytest.mark.asyncio
    async def test_clear_uses_current_channel(self, mock_context, patched_clear_history):
        from tests.conftest import AsyncContextManager

        patched_clear_history.return_value = 1
        plugin = _build_plugin()
        plugin.db_session.return_value = AsyncContextManager(MagicMock())

        await _handle_clear(plugin, mock_context)

        args, kwargs = patched_clear_history.call_args
        # clear_history(session, guild_id, channel_id) — args[0] is the session.
        guild_id = args[1] if len(args) > 1 else kwargs.get("guild_id")
        channel_id = args[2] if len(args) > 2 else kwargs.get("channel_id")
        assert guild_id == mock_context.guild_id
        assert channel_id == mock_context.channel_id

    @pytest.mark.asyncio
    async def test_clearai_command_metadata_has_alias(self):
        """The clearai command declares the clearchat alias and permission node."""
        from plugins.ai.commands.clear import setup_clear_commands

        plugin = MagicMock()
        commands = setup_clear_commands(plugin)
        assert len(commands) == 1
        cmd = commands[0]
        meta = cmd._prefix_command
        assert meta["name"] == "clearai"
        assert "clearchat" in meta["aliases"]
        assert meta["permission_node"] == "basic.ai.clear"

    @pytest.mark.asyncio
    async def test_clearai_unexpected_error_responds_error(self, mock_context, patched_clear_history):
        from tests.conftest import AsyncContextManager

        patched_clear_history.side_effect = RuntimeError("db down")
        plugin = _build_plugin()
        plugin.db_session.return_value = AsyncContextManager(MagicMock())

        await _handle_clear(plugin, mock_context)

        plugin.respond_error.assert_awaited_once()
