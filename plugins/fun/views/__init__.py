from __future__ import annotations

import logging
import random
from typing import Any

import hikari
import miru

from ..config import fun_settings

logger = logging.getLogger(__name__)


class WouldYouRatherView(miru.View):
    """Interactive would you rather view with voting buttons."""

    def __init__(self, option_a: str, option_b: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(timeout=fun_settings.content_view_timeout_seconds, *args, **kwargs)
        self.option_a = option_a
        self.option_b = option_b
        self.votes_a: set[int] = set()
        self.votes_b: set[int] = set()

        button_a = miru.Button(
            style=hikari.ButtonStyle.PRIMARY,
            label="Option A",
            emoji="🅰️",
            custom_id="wyr_option_a",
        )
        button_a.callback = self.vote_option_a
        self.add_item(button_a)

        button_b = miru.Button(
            style=hikari.ButtonStyle.SECONDARY,
            label="Option B",
            emoji="🅱️",
            custom_id="wyr_option_b",
        )
        button_b.callback = self.vote_option_b
        self.add_item(button_b)

    async def vote_option_a(self, ctx: miru.ViewContext) -> None:
        user_id = ctx.user.id
        self.votes_b.discard(user_id)

        if user_id in self.votes_a:
            self.votes_a.discard(user_id)
            await ctx.respond("Removed your vote for Option A!", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            self.votes_a.add(user_id)
            await ctx.respond("Voted for Option A!", flags=hikari.MessageFlag.EPHEMERAL)

        await self._update_results(ctx)

    async def vote_option_b(self, ctx: miru.ViewContext) -> None:
        user_id = ctx.user.id
        self.votes_a.discard(user_id)

        if user_id in self.votes_b:
            self.votes_b.discard(user_id)
            await ctx.respond("Removed your vote for Option B!", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            self.votes_b.add(user_id)
            await ctx.respond("Voted for Option B!", flags=hikari.MessageFlag.EPHEMERAL)

        await self._update_results(ctx)

    async def _update_results(self, ctx: miru.ViewContext) -> None:
        total_votes = len(self.votes_a) + len(self.votes_b)

        if total_votes == 0:
            percent_a = percent_b = 0.0
        else:
            percent_a = (len(self.votes_a) / total_votes) * 100
            percent_b = (len(self.votes_b) / total_votes) * 100

        bar_length = 10
        filled_a = int((percent_a / 100) * bar_length)
        filled_b = int((percent_b / 100) * bar_length)

        bar_a = "█" * filled_a + "░" * (bar_length - filled_a)
        bar_b = "█" * filled_b + "░" * (bar_length - filled_b)

        embed = hikari.Embed(
            title="🤔 Would You Rather... (Live Results)",
            color=hikari.Color(0xFF1493),
        )

        embed.add_field(
            "🅰️ Option A",
            f"{self.option_a}\n\n{bar_a} {len(self.votes_a)} votes ({percent_a:.1f}%)",
            inline=True,
        )

        embed.add_field(
            "🅱️ Option B",
            f"{self.option_b}\n\n{bar_b} {len(self.votes_b)} votes ({percent_b:.1f}%)",
            inline=True,
        )

        embed.set_footer(f"Total votes: {total_votes} • Click buttons to vote!")

        try:
            await ctx.edit_response(embed=embed, components=self)
        except Exception:  # best-effort update
            pass