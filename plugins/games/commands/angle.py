"""Angle guessing game command — daily challenge inspired by angle.wtf."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import ANGLE_MAX_ATTEMPTS, EMBED_COLORS
from ..utils.angle_image import generate_angle_image
from ..views.angle import AngleView, _build_angle_embed

if TYPE_CHECKING:
    from ..plugin import GamesPlugin

logger = logging.getLogger(__name__)


def setup_angle_commands(plugin: GamesPlugin) -> list[Callable[..., Any]]:
    """Register the /angle family of commands."""

    @command(
        name="angle",
        description="Daily angle guessing game — 4 attempts to guess the mystery angle (inspired by angle.wtf)",
        permission_node="basic.games.angle.play",
    )
    async def angle_game(ctx: lightbulb.Context) -> None:
        try:
            if not ctx.guild_id:
                embed = plugin.create_embed(
                    title="❌ Error",
                    description="Angle can only be played in servers, not in DMs!",
                    color=hikari.Color(EMBED_COLORS["error"]),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            state = await plugin.get_or_create_angle_game(ctx.author.id, ctx.guild_id)

            is_complete = state.get("is_complete", False)
            target_reveal = state["target"] if is_complete else None
            image_bytes = generate_angle_image(state["guesses"], target=target_reveal)

            user_mention = ctx.author.mention
            embed = _build_angle_embed(plugin, state, user_mention)
            attachment = hikari.Bytes(image_bytes, "angle.png")
            embed.set_image(attachment)

            miru_client = getattr(plugin.bot, "miru_client", None)

            if is_complete:
                # Game already finished — just show the result, no button
                await ctx.respond(embed=embed)
            elif miru_client:
                view = AngleView(plugin, ctx.author.id, ctx.guild_id, state)
                response = await ctx.respond(embed=embed, components=view)
                miru_client.start_view(view, bind_to=response)
            else:
                await ctx.respond(embed=embed)

            await plugin.log_command_usage(ctx, "angle", True)

        except Exception as exc:
            logger.error("Error in angle command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to start the angle game. Try again later!",
                color=hikari.Color(EMBED_COLORS["error"]),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "angle", False, str(exc))

    @command(
        name="angle-stats",
        description="View your daily angle game statistics",
        permission_node="basic.games.angle.play",
        arguments=[
            CommandArgument(
                "user",
                hikari.OptionType.USER,
                "User to view stats for",
                required=False,
            ),
        ],
    )
    async def angle_stats(ctx: lightbulb.Context, user: hikari.User | None = None) -> None:
        target_user = user or ctx.author

        try:
            stats = await plugin.get_angle_stats(target_user.id, ctx.guild_id)

            if not stats or stats.total_games == 0:
                embed = plugin.create_embed(
                    title="📐 Angle Statistics",
                    description=f"{target_user.mention} hasn't played the angle game yet!\nRun `/angle` to play.",
                    color=hikari.Color(EMBED_COLORS["info"]),
                )
            else:
                embed = plugin.create_embed(
                    title=f"📐 Angle Statistics — {target_user.username}",
                    color=hikari.Color(EMBED_COLORS["angle"]),
                )
                embed.add_field(
                    "📊 Overall",
                    f"**Games Played:** {stats.total_games:,}\n"
                    f"**Wins:** {stats.wins:,}\n"
                    f"**Win Rate:** {stats.win_rate:.1f}%\n"
                    f"**Total Points:** {stats.total_points:,}",
                    inline=True,
                )
                embed.add_field(
                    "🎯 Precision",
                    f"**Perfect guesses:** {stats.exact_wins:,}\n"
                    f"**Close wins (≤2°):** {stats.close_wins:,}",
                    inline=True,
                )
                embed.add_field(
                    "🔥 Streaks",
                    f"**Current streak:** {stats.current_win_streak}\n"
                    f"**Best streak:** {stats.best_win_streak}",
                    inline=True,
                )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "angle-stats", True)

        except Exception as exc:
            logger.error("Error in angle-stats command: %s", exc)
            await plugin.log_command_usage(ctx, "angle-stats", False, str(exc))

    return [angle_game, angle_stats]
