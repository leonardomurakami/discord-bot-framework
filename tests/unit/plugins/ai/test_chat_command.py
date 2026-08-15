"""Tests for the AI plugin `chat` command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from plugins.ai.commands.chat import _handle_chat
from plugins.ai.config import MAX_PROMPT_LENGTH
from plugins.ai.utils import (
    AcpboxEmptyChoicesError,
    AcpboxHTTPError,
    AcpboxRateLimitError,
    AcpboxUnreachableError,
)
from tests.conftest import AsyncContextManager


def _build_plugin(mock_bot, *, session_set: bool = True) -> MagicMock:
    """Build a mock AIPlugin with the attributes the chat handler touches."""
    plugin = MagicMock()
    plugin.session = MagicMock(spec=aiohttp.ClientSession) if session_set else None
    plugin.db_session = MagicMock(return_value=AsyncContextManager(MagicMock()))
    plugin.respond_error = AsyncMock()
    plugin.respond_success = AsyncMock()
    plugin.smart_respond = AsyncMock()
    plugin.log_command_usage = AsyncMock()
    return plugin


@pytest.fixture
def patched_settings():
    """Patch config.settings.settings for the chat handler scope."""
    with patch("plugins.ai.commands.chat.settings") as mock_settings:
        mock_settings.ai_system_prompt = "You are a helpful assistant."
        mock_settings.ai_model = "gpt-test"
        mock_settings.ai_memory_turns = 2
        yield mock_settings


@pytest.fixture
def patched_load_history():
    with patch("plugins.ai.commands.chat.load_history", new_callable=AsyncMock) as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def patched_append_turn():
    with patch("plugins.ai.commands.chat.append_turn", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def patched_call_acpbox():
    with patch("plugins.ai.commands.chat.call_acpbox", new_callable=AsyncMock) as mock:
        mock.return_value = "Sure! Here is the answer."
        yield mock


@pytest.fixture
def patched_build_reply():
    with patch("plugins.ai.commands.chat.build_reply_text", return_value="Sure! Here is the answer.\n\n_— model: gpt-test_") as mock:
        yield mock


class TestChatCommand:
    @pytest.mark.asyncio
    async def test_successful_invocation(
        self,
        mock_context,
        patched_settings,
        patched_load_history,
        patched_append_turn,
        patched_call_acpbox,
        patched_build_reply,
    ):
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "What is Hikari?")

        patched_call_acpbox.assert_awaited_once()
        plugin.smart_respond.assert_awaited_once()
        plugin.log_command_usage.assert_awaited_once()
        # Both user and assistant turns are appended.
        assert patched_append_turn.await_count == 2

    @pytest.mark.asyncio
    async def test_missing_message_responds_error(self, mock_context, patched_settings, patched_call_acpbox):
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "")

        plugin.respond_error.assert_awaited_once()
        patched_call_acpbox.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_message_responds_error(self, mock_context, patched_settings, patched_call_acpbox):
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "   ")

        plugin.respond_error.assert_awaited_once()
        patched_call_acpbox.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_over_length_prompt_responds_error(self, mock_context, patched_settings, patched_call_acpbox):
        plugin = _build_plugin(mock_bot=MagicMock())
        long_msg = "x" * (MAX_PROMPT_LENGTH + 1)
        await _handle_chat(plugin, mock_context, long_msg)

        plugin.respond_error.assert_awaited_once()
        patched_call_acpbox.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_session_unavailable_responds_error(self, mock_context, patched_settings, patched_call_acpbox):
        plugin = _build_plugin(mock_bot=MagicMock(), session_set=False)
        await _handle_chat(plugin, mock_context, "hi")

        plugin.respond_error.assert_awaited_once()
        # The error message references configuration.
        args, _ = plugin.respond_error.call_args
        assert "not configured" in args[1].lower() or "ACPBOX_URL" in args[1]
        patched_call_acpbox.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_endpoint_unreachable_responds_error(
        self, mock_context, patched_settings, patched_load_history, patched_call_acpbox
    ):
        patched_call_acpbox.side_effect = AcpboxUnreachableError("down")
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "hi")

        plugin.respond_error.assert_awaited_once()
        args, _ = plugin.respond_error.call_args
        assert "unreachable" in args[1].lower()

    @pytest.mark.asyncio
    async def test_rate_limited_responds_error(self, mock_context, patched_settings, patched_load_history, patched_call_acpbox):
        patched_call_acpbox.side_effect = AcpboxRateLimitError("limited")
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "hi")

        plugin.respond_error.assert_awaited_once()
        args, _ = plugin.respond_error.call_args
        assert "rate-limited" in args[1].lower()

    @pytest.mark.asyncio
    async def test_empty_choices_responds_error(self, mock_context, patched_settings, patched_load_history, patched_call_acpbox):
        patched_call_acpbox.side_effect = AcpboxEmptyChoicesError("no response")
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "hi")

        plugin.respond_error.assert_awaited_once()
        args, _ = plugin.respond_error.call_args
        assert "no response" in args[1].lower()

    @pytest.mark.asyncio
    async def test_http_error_responds_error_with_status(
        self, mock_context, patched_settings, patched_load_history, patched_call_acpbox
    ):
        patched_call_acpbox.side_effect = AcpboxHTTPError(503, "service unavailable")
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "hi")

        plugin.respond_error.assert_awaited_once()
        args, _ = plugin.respond_error.call_args
        assert "503" in args[1]

    @pytest.mark.asyncio
    async def test_history_included_in_messages(
        self,
        mock_context,
        patched_settings,
        patched_load_history,
        patched_append_turn,
        patched_call_acpbox,
        patched_build_reply,
    ):
        patched_load_history.return_value = [
            {"role": "user", "content": "earlier question"},
            {"role": "assistant", "content": "earlier answer"},
        ]
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "follow up")

        # Inspect the messages list passed to call_acpbox.
        args, kwargs = patched_call_acpbox.call_args
        messages = args[2] if len(args) > 2 else kwargs["messages"]
        roles = [m["role"] for m in messages]
        assert roles == ["system", "user", "assistant", "user"]
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[-1]["content"] == "follow up"

    @pytest.mark.asyncio
    async def test_history_truncation_uses_memory_turns(
        self,
        mock_context,
        patched_settings,
        patched_load_history,
        patched_append_turn,
        patched_call_acpbox,
        patched_build_reply,
    ):
        # load_history is responsible for truncating; the handler just passes whatever it returns.
        patched_load_history.return_value = [{"role": "user", "content": "recent"}]
        plugin = _build_plugin(mock_bot=MagicMock())
        await _handle_chat(plugin, mock_context, "next")

        patched_load_history.assert_awaited_once()
        args, kwargs = patched_load_history.call_args
        # memory_turns comes from patched_settings.ai_memory_turns == 2
        assert kwargs.get("memory_turns") == 2 or args[-1] == 2
