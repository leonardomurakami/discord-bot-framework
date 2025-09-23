from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari

from bot.plugins.commands import command

if TYPE_CHECKING:
    from ..plugin import FunPlugin

logger = logging.getLogger(__name__)


def setup_basic_commands(plugin: FunPlugin) -> list[Callable[..., Any]]:
    """Register simple utility commands like ping."""

    @command(name="ping", description="Test command - check if bot is responding")
    async def ping_command(ctx) -> None:
        try:
            logger.info("Ping command called by %s", ctx.author.username)
            embed = plugin.create_embed(
                title="🏓 Pong!",
                description="Bot is working correctly!",
                color=hikari.Color(0x00FF00),
            )
            await ctx.respond(embed=embed)
            logger.info("Ping command responded successfully")
        except Exception as exc:
            logger.error("Error in ping command: %s", exc)

    return [ping_command]
