from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command
from config.settings import settings

from ..config import MAX_PROMPT_LENGTH
from ..utils import (
    AcpboxEmptyChoicesError,
    AcpboxHTTPError,
    AcpboxRateLimitError,
    AcpboxUnreachableError,
    append_turn,
    build_reply_text,
    call_acpbox,
    load_history,
)

if TYPE_CHECKING:
    from ..plugin import AIPlugin

logger = logging.getLogger(__name__)


def setup_chat_commands(plugin: AIPlugin) -> list[Callable[..., Any]]:
    """Register the unified `chat` command."""

    @command(
        name="chat",
        description="Chat with the AI",
        permission_node="basic.ai.chat",
        arguments=[
            CommandArgument(
                "message",
                hikari.OptionType.STRING,
                "Your message to the AI",
                required=True,
            )
        ],
    )
    async def chat_command(ctx: lightbulb.Context, message: str = "") -> None:
        await _handle_chat(plugin, ctx, message)

    return [chat_command]


async def _handle_chat(plugin: AIPlugin, ctx: lightbulb.Context, message: str) -> None:
    command_name = "chat"
    try:
        if not message or not message.strip():
            await plugin.respond_error(ctx, "Please provide a message to send to the AI.", command_name=command_name)
            return

        if len(message) > MAX_PROMPT_LENGTH:
            await plugin.respond_error(
                ctx,
                f"Your message is too long (max {MAX_PROMPT_LENGTH} characters).",
                command_name=command_name,
            )
            return

        if plugin.session is None:
            await plugin.respond_error(
                ctx,
                "The AI service is not configured. An admin must set ACPBOX_URL and AI_MODEL.",
                command_name=command_name,
            )
            return

        guild_id = ctx.guild_id or 0
        channel_id = ctx.channel_id or 0

        # Load retained history and build the messages list.
        async with plugin.db_session() as session:
            history = await load_history(session, guild_id, channel_id, settings.ai_memory_turns)

        messages = [{"role": "system", "content": settings.ai_system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        # Call the acpbox endpoint.
        reply = await call_acpbox(plugin.session, settings, messages)

        # Persist the user and assistant turns.
        async with plugin.db_session() as session:
            await append_turn(session, guild_id, channel_id, "user", message, settings.ai_memory_turns)
            await append_turn(session, guild_id, channel_id, "assistant", reply, settings.ai_memory_turns)

        text = build_reply_text(reply, settings.ai_model)
        await plugin.smart_respond(ctx, content=text)
        await plugin.log_command_usage(ctx, command_name, True)
    except AcpboxUnreachableError as exc:
        logger.error("chat command acpbox unreachable: %s", exc)
        await plugin.respond_error(ctx, "The AI service is unreachable. Please try again later.", command_name=command_name)
    except AcpboxRateLimitError as exc:
        logger.warning("chat command acpbox rate limited: %s", exc)
        await plugin.respond_error(ctx, "The AI service is rate-limited. Please try again shortly.", command_name=command_name)
    except AcpboxEmptyChoicesError as exc:
        logger.warning("chat command empty choices: %s", exc)
        await plugin.respond_error(
            ctx,
            "The AI returned no response. Please try rephrasing your message.",
            command_name=command_name,
        )
    except AcpboxHTTPError as exc:
        logger.error("chat command acpbox http %s: %s", exc.status, exc.body[:500])
        body_preview = (exc.body or "")[:200]
        await plugin.respond_error(
            ctx,
            f"The AI service returned an error (HTTP {exc.status}).\n```{body_preview}```",
            command_name=command_name,
        )
    except Exception as exc:  # pragma: no cover - defensive catch-all
        logger.exception("chat command unexpected error: %s", exc)
        await plugin.respond_error(
            ctx,
            "An unexpected error occurred while contacting the AI service.",
            command_name=command_name,
        )
