from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import lightbulb

from bot.plugins.commands import command

from ..utils import clear_history

if TYPE_CHECKING:
    from ..plugin import AIPlugin

logger = logging.getLogger(__name__)


def setup_clear_commands(plugin: AIPlugin) -> list[Callable[..., Any]]:
    """Register the unified `clearai` command."""

    @command(
        name="clearai",
        description="Clear this channel's AI history",
        aliases=["clearchat"],
        permission_node="basic.ai.clear",
    )
    async def clearai_command(ctx: lightbulb.Context) -> None:
        await _handle_clear(plugin, ctx)

    return [clearai_command]


async def _handle_clear(plugin: AIPlugin, ctx: lightbulb.Context) -> None:
    command_name = "clearai"
    try:
        guild_id = ctx.guild_id or 0
        channel_id = ctx.channel_id or 0

        async with plugin.db_session() as session:
            deleted = await clear_history(session, guild_id, channel_id)

        if deleted > 0:
            await plugin.respond_success(
                ctx,
                f"Cleared {deleted} AI conversation row(s) for this channel.",
                command_name=command_name,
            )
        else:
            await plugin.respond_success(
                ctx,
                "There was no AI history to clear for this channel.",
                command_name=command_name,
            )
    except Exception as exc:  # pragma: no cover - defensive catch-all
        logger.exception("clearai command unexpected error: %s", exc)
        await plugin.respond_error(ctx, "An unexpected error occurred while clearing AI history.", command_name=command_name)
