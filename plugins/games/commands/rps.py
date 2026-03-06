"""Rock Paper Scissors command."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

from bot.plugins.commands import command

from ..config import EMBED_COLORS
from ..views.rps import RPSView

if TYPE_CHECKING:
    from ..plugin import GamesPlugin

logger = logging.getLogger(__name__)


def setup_rps_commands(plugin: GamesPlugin) -> list[Callable[..., Any]]:
    """Register the /rps command."""

    @command(
        name="rps",
        description="Play Rock Paper Scissors against the bot",
        permission_node="basic.games.rps.play",
    )
    async def rps(ctx: lightbulb.Context) -> None:
        try:
            embed = plugin.create_embed(
                title="🪨📄✂️ Rock Paper Scissors",
                description="Choose your move below!",
                color=hikari.Color(EMBED_COLORS["rps"]),
            )

            miru_client = getattr(plugin.bot, "miru_client", None)
            if miru_client:
                view = RPSView(plugin, ctx.author.id)
                response = await ctx.respond(embed=embed, components=view)
                miru_client.start_view(view, bind_to=response)
            else:
                await ctx.respond(embed=embed)

            await plugin.log_command_usage(ctx, "rps", True)

        except Exception as exc:
            logger.error("Error in rps command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to start Rock Paper Scissors. Try again later!",
                color=hikari.Color(EMBED_COLORS["error"]),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "rps", False, str(exc))

    return [rps]
