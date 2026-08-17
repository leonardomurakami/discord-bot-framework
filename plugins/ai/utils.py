"""AI client and conversation-history helpers for an OpenAI-compatible Chat Completions endpoint."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from .config import CHAT_COMPLETIONS_PATH, DISCORD_MESSAGE_LIMIT, FOOTER_RESERVE, FOOTER_TEMPLATE, TRUNCATION_INDICATOR

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class AIClientError(Exception):
    """Base error for AI API failures surfaced to the user as an error embed."""


class AIClientUnreachableError(AIClientError):
    """Endpoint could not be reached (connection error or timeout)."""


class AIClientHTTPError(AIClientError):
    """Endpoint returned a non-2xx status code."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body


class AIClientRateLimitError(AIClientError):
    """Endpoint returned HTTP 429."""


class AIClientEmptyChoicesError(AIClientError):
    """Endpoint returned a 2xx response with an empty choices array."""


# ---------------------------------------------------------------------------
# HTTP call
# ---------------------------------------------------------------------------


async def call_ai(
    session: aiohttp.ClientSession,
    settings_obj: Any,
    messages: list[dict[str, str]],
) -> str:
    """Send a Chat Completions request to the OpenAI-compatible endpoint and return the assistant text.

    Args:
        session: aiohttp ClientSession managed by the plugin lifecycle.
        settings_obj: Settings object exposing ai_base_url, ai_model, ai_api_key,
            ai_max_tokens, and ai_temperature.
        messages: OpenAI-style messages list (system/user/assistant dicts).

    Returns:
        The assistant message content from choices[0].

    Raises:
        AIClientUnreachableError: connection error or timeout.
        AIClientRateLimitError: HTTP 429.
        AIClientHTTPError: any other non-2xx status.
        AIClientEmptyChoicesError: 2xx with no choices.
    """
    url = f"{settings_obj.ai_base_url.rstrip('/')}{CHAT_COMPLETIONS_PATH}"
    headers = {"Content-Type": "application/json"}
    if settings_obj.ai_api_key:
        headers["Authorization"] = f"Bearer {settings_obj.ai_api_key}"

    payload = {
        "model": settings_obj.ai_model,
        "messages": messages,
        "max_tokens": settings_obj.ai_max_tokens,
        "temperature": settings_obj.ai_temperature,
    }

    try:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 429:
                body = await _safe_text(resp)
                logger.warning("AI API rate limited (429): %s", body[:500])
                raise AIClientRateLimitError("AI service is rate-limited; try again shortly.")
            if resp.status < 200 or resp.status >= 300:
                body = await _safe_text(resp)
                logger.error("AI API non-2xx %s: %s", resp.status, body[:1000])
                raise AIClientHTTPError(resp.status, body)

            data = await resp.json()
    except aiohttp.ClientError as exc:
        logger.error("AI API unreachable: %s", exc)
        raise AIClientUnreachableError("AI service is unreachable.") from exc
    except TimeoutError as exc:  # aiohttp raises asyncio.TimeoutError on total timeout
        logger.error("AI API timeout: %s", exc)
        raise AIClientUnreachableError("AI service timed out.") from exc

    choices = data.get("choices") or []
    if not choices:
        logger.warning("AI API returned 2xx with empty choices: %s", str(data)[:500])
        raise AIClientEmptyChoicesError("AI returned no response.")

    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if not content:
        raise AIClientEmptyChoicesError("AI returned an empty response.")
    return content


async def _safe_text(resp: aiohttp.ClientResponse) -> str:
    try:
        return await resp.text()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Conversation history helpers
# ---------------------------------------------------------------------------


async def load_history(
    session: AsyncSession,
    guild_id: int,
    channel_id: int,
    memory_turns: int,
) -> list[dict[str, str]]:
    """Load the last ``2 * memory_turns`` rows for a channel as OpenAI message dicts."""
    from sqlalchemy import select

    from .models import AIConversation

    limit = max(1, memory_turns) * 2
    result = await session.execute(
        select(AIConversation)
        .where(
            AIConversation.guild_id == guild_id,
            AIConversation.channel_id == channel_id,
        )
        .order_by(AIConversation.created_at.desc())
        .limit(limit)
    )
    rows = list(result.scalars().all())
    rows.reverse()  # chronological order for the request
    return [{"role": r.role, "content": r.content} for r in rows]


async def append_turn(
    session: AsyncSession,
    guild_id: int,
    channel_id: int,
    role: str,
    content: str,
    memory_turns: int,
) -> None:
    """Insert a new turn and prune rows beyond ``2 * memory_turns`` for the channel."""
    from sqlalchemy import delete, func, select

    from .models import AIConversation

    session.add(
        AIConversation(
            guild_id=guild_id,
            channel_id=channel_id,
            role=role,
            content=content,
        )
    )
    await session.flush()

    max_rows = max(1, memory_turns) * 2
    count_result = await session.execute(
        select(func.count(AIConversation.id)).where(
            AIConversation.guild_id == guild_id,
            AIConversation.channel_id == channel_id,
        )
    )
    total = count_result.scalar_one()
    if total > max_rows:
        # Delete the oldest rows beyond the limit.
        subq = (
            select(AIConversation.id)
            .where(
                AIConversation.guild_id == guild_id,
                AIConversation.channel_id == channel_id,
            )
            .order_by(AIConversation.created_at.desc())
            .limit(max_rows)
        ).subquery()
        await session.execute(delete(AIConversation).where(AIConversation.id.not_in(select(subq.c.id))))


async def clear_history(
    session: AsyncSession,
    guild_id: int,
    channel_id: int,
) -> int:
    """Delete all history rows for a channel and return the deleted count."""
    from sqlalchemy import delete, func, select

    from .models import AIConversation

    count_result = await session.execute(
        select(func.count(AIConversation.id)).where(
            AIConversation.guild_id == guild_id,
            AIConversation.channel_id == channel_id,
        )
    )
    total = count_result.scalar_one()
    await session.execute(
        delete(AIConversation).where(
            AIConversation.guild_id == guild_id,
            AIConversation.channel_id == channel_id,
        )
    )
    return total


# ---------------------------------------------------------------------------
# Reply formatting
# ---------------------------------------------------------------------------


def build_reply_text(content: str, model_name: str | None) -> str:
    """Truncate ``content`` to fit Discord's message limit and append a model-crediting footer."""
    footer = FOOTER_TEMPLATE.format(model=model_name or "unknown")
    max_content = DISCORD_MESSAGE_LIMIT - FOOTER_RESERVE
    if len(content) > max_content:
        content = content[: max_content - 1] + TRUNCATION_INDICATOR
    return content + footer
