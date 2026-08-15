"""Tests for plugins.ai.utils."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from plugins.ai.config import DISCORD_MESSAGE_LIMIT
from plugins.ai.utils import (
    AcpboxEmptyChoicesError,
    AcpboxHTTPError,
    AcpboxRateLimitError,
    AcpboxUnreachableError,
    append_turn,
    build_reply_text,
    call_acpbox,
    clear_history,
    load_history,
)
from tests.unit.plugins.ai.conftest import make_turn

# ---------------------------------------------------------------------------
# call_acpbox
# ---------------------------------------------------------------------------


def _mock_response(status: int, json_data: dict | None = None, text: str = "") -> MagicMock:
    """Build a mock aiohttp ClientResponse."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.text = AsyncMock(return_value=text)
    return resp


def _mock_session(resp: MagicMock) -> MagicMock:
    """Build a mock aiohttp ClientSession whose POST returns a CM yielding ``resp``."""
    session = MagicMock(spec=aiohttp.ClientSession)
    post_cm = MagicMock()
    post_cm.__aenter__ = AsyncMock(return_value=resp)
    post_cm.__aexit__ = AsyncMock(return_value=None)
    session.post = MagicMock(return_value=post_cm)
    return session


class TestCallAcpbox:
    @pytest.mark.asyncio
    async def test_success_returns_assistant_content(self, ai_settings):
        resp = _mock_response(200, {"choices": [{"message": {"content": "Hello there!"}}]})
        session = _mock_session(resp)

        result = await call_acpbox(session, ai_settings, [{"role": "user", "content": "hi"}])

        assert result == "Hello there!"

    @pytest.mark.asyncio
    async def test_request_body_shape(self, ai_settings):
        resp = _mock_response(200, {"choices": [{"message": {"content": "ok"}}]})
        session = _mock_session(resp)

        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
        await call_acpbox(session, ai_settings, messages)

        args, kwargs = session.post.call_args
        # URL is acpbox_url + /v1/chat/completions
        assert args[0] == "http://acpbox.local:8080/v1/chat/completions"
        body = kwargs["json"]
        assert body["model"] == "gpt-test"
        assert body["messages"] == messages
        assert body["max_tokens"] == 1000
        assert body["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_auth_header_present_when_key_set(self, ai_settings_with_key):
        resp = _mock_response(200, {"choices": [{"message": {"content": "ok"}}]})
        session = _mock_session(resp)

        await call_acpbox(session, ai_settings_with_key, [{"role": "user", "content": "hi"}])

        _, kwargs = session.post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer secret-key"

    @pytest.mark.asyncio
    async def test_auth_header_absent_when_key_unset(self, ai_settings):
        resp = _mock_response(200, {"choices": [{"message": {"content": "ok"}}]})
        session = _mock_session(resp)

        await call_acpbox(session, ai_settings, [{"role": "user", "content": "hi"}])

        _, kwargs = session.post.call_args
        assert "Authorization" not in kwargs["headers"]

    @pytest.mark.asyncio
    async def test_rate_limit_raises(self, ai_settings):
        resp = _mock_response(429, text="rate limited")
        session = _mock_session(resp)

        with pytest.raises(AcpboxRateLimitError):
            await call_acpbox(session, ai_settings, [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_non_2xx_raises_http_error(self, ai_settings):
        resp = _mock_response(500, text="internal error")
        session = _mock_session(resp)

        with pytest.raises(AcpboxHTTPError) as exc_info:
            await call_acpbox(session, ai_settings, [{"role": "user", "content": "hi"}])

        assert exc_info.value.status == 500
        assert "internal error" in exc_info.value.body

    @pytest.mark.asyncio
    async def test_empty_choices_raises(self, ai_settings):
        resp = _mock_response(200, {"choices": []})
        session = _mock_session(resp)

        with pytest.raises(AcpboxEmptyChoicesError):
            await call_acpbox(session, ai_settings, [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_empty_content_raises(self, ai_settings):
        resp = _mock_response(200, {"choices": [{"message": {"content": ""}}]})
        session = _mock_session(resp)

        with pytest.raises(AcpboxEmptyChoicesError):
            await call_acpbox(session, ai_settings, [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_connection_error_raises_unreachable(self, ai_settings):
        session = MagicMock(spec=aiohttp.ClientSession)
        post_cm = MagicMock()
        post_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientConnectionError("boom"))
        post_cm.__aexit__ = AsyncMock(return_value=None)
        session.post = MagicMock(return_value=post_cm)

        with pytest.raises(AcpboxUnreachableError):
            await call_acpbox(session, ai_settings, [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_timeout_raises_unreachable(self, ai_settings):
        session = MagicMock(spec=aiohttp.ClientSession)
        post_cm = MagicMock()
        post_cm.__aenter__ = AsyncMock(side_effect=TimeoutError())
        post_cm.__aexit__ = AsyncMock(return_value=None)
        session.post = MagicMock(return_value=post_cm)

        with pytest.raises(AcpboxUnreachableError):
            await call_acpbox(session, ai_settings, [{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------


class TestLoadHistory:
    @pytest.mark.asyncio
    async def test_returns_chronological_order(self, ai_db_session):
        session = ai_db_session
        session.add(make_turn(role="user", content="first", offset_seconds=0))
        session.add(make_turn(role="assistant", content="first-reply", offset_seconds=1))
        session.add(make_turn(role="user", content="second", offset_seconds=2))
        await session.commit()

        history = await load_history(session, guild_id=1, channel_id=2, memory_turns=10)

        assert [m["content"] for m in history] == ["first", "first-reply", "second"]
        assert [m["role"] for m in history] == ["user", "assistant", "user"]

    @pytest.mark.asyncio
    async def test_limits_to_2x_memory_turns(self, ai_db_session):
        session = ai_db_session
        # Insert 6 rows (3 turns); memory_turns=2 should return only the last 4 rows.
        for i in range(6):
            session.add(make_turn(role="user" if i % 2 == 0 else "assistant", content=f"msg{i}", offset_seconds=i))
        await session.commit()

        history = await load_history(session, guild_id=1, channel_id=2, memory_turns=2)

        assert len(history) == 4
        assert history[0]["content"] == "msg2"
        assert history[-1]["content"] == "msg5"

    @pytest.mark.asyncio
    async def test_empty_when_no_history(self, ai_db_session):
        history = await load_history(ai_db_session, guild_id=1, channel_id=2, memory_turns=5)
        assert history == []


class TestAppendTurn:
    @pytest.mark.asyncio
    async def test_inserts_row(self, ai_db_session):
        await append_turn(ai_db_session, guild_id=1, channel_id=2, role="user", content="hello", memory_turns=5)
        await ai_db_session.flush()

        from sqlalchemy import select

        result = await ai_db_session.execute(select(__import__("plugins.ai.models", fromlist=["AIConversation"]).AIConversation))
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].content == "hello"
        assert rows[0].role == "user"

    @pytest.mark.asyncio
    async def test_prunes_beyond_limit(self, ai_db_session):
        # memory_turns=1 => max 2 rows. Insert 3 rows one at a time; only 2 should remain.
        for i in range(3):
            await append_turn(ai_db_session, guild_id=1, channel_id=2, role="user", content=f"m{i}", memory_turns=1)
            await ai_db_session.flush()

        from sqlalchemy import select

        from plugins.ai.models import AIConversation

        result = await ai_db_session.execute(
            select(AIConversation).where(AIConversation.guild_id == 1, AIConversation.channel_id == 2)
        )
        rows = result.scalars().all()
        assert len(rows) == 2
        contents = {r.content for r in rows}
        assert contents == {"m1", "m2"}


class TestClearHistory:
    @pytest.mark.asyncio
    async def test_returns_zero_when_empty(self, ai_db_session):
        deleted = await clear_history(ai_db_session, guild_id=1, channel_id=2)
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_deletes_all_rows(self, ai_db_session):
        session = ai_db_session
        session.add(make_turn(role="user", content="a"))
        session.add(make_turn(role="assistant", content="b"))
        await session.commit()

        deleted = await clear_history(session, guild_id=1, channel_id=2)
        assert deleted == 2

        from sqlalchemy import select

        from plugins.ai.models import AIConversation

        result = await session.execute(select(AIConversation).where(AIConversation.guild_id == 1, AIConversation.channel_id == 2))
        assert result.scalars().all() == []


# ---------------------------------------------------------------------------
# Reply formatting
# ---------------------------------------------------------------------------


class TestBuildReplyText:
    def test_appends_model_footer(self):
        text = build_reply_text("Hello!", "gpt-test")
        assert "Hello!" in text
        assert "gpt-test" in text

    def test_truncates_over_length_content(self):
        long_content = "x" * (DISCORD_MESSAGE_LIMIT + 500)
        text = build_reply_text(long_content, "gpt-test")
        assert len(text) <= DISCORD_MESSAGE_LIMIT
        assert text.endswith("…\n\n_— model: gpt-test_") or "…" in text

    def test_short_content_not_truncated(self):
        text = build_reply_text("short", "gpt-test")
        assert text.startswith("short")
        assert "gpt-test" in text
