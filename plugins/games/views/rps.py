"""Rock Paper Scissors interactive view."""
from __future__ import annotations

import random
import logging
from typing import TYPE_CHECKING

import hikari
import miru

from ..config import EMBED_COLORS

if TYPE_CHECKING:
    from ..plugin import GamesPlugin

logger = logging.getLogger(__name__)

_CHOICES = {
    "rock": {"emoji": "🪨", "label": "Rock", "beats": "scissors"},
    "paper": {"emoji": "📄", "label": "Paper", "beats": "rock"},
    "scissors": {"emoji": "✂️", "label": "Scissors", "beats": "paper"},
}


def _determine_result(player: str, bot_choice: str) -> str:
    """Return 'win', 'lose', or 'draw'."""
    if player == bot_choice:
        return "draw"
    if _CHOICES[player]["beats"] == bot_choice:
        return "win"
    return "lose"


class RPSView(miru.View):
    """Show three buttons (Rock / Paper / Scissors); resolve immediately on click."""

    def __init__(self, plugin: GamesPlugin, invoker_id: int) -> None:
        super().__init__(timeout=60)
        self.plugin = plugin
        self.invoker_id = invoker_id

    async def _handle_choice(self, ctx: miru.ViewContext, player_choice: str) -> None:
        if ctx.user.id != self.invoker_id:
            await ctx.respond(
                "This isn't your game! Run `/rps` to start your own.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return

        bot_choice = random.choice(list(_CHOICES.keys()))
        result = _determine_result(player_choice, bot_choice)

        player_info = _CHOICES[player_choice]
        bot_info = _CHOICES[bot_choice]

        if result == "win":
            title = "🎉 You win!"
            color = hikari.Color(0x57F287)   # green
            description = f"**{player_info['emoji']} {player_info['label']}** beats **{bot_info['emoji']} {bot_info['label']}**!"
        elif result == "lose":
            title = "💀 You lose!"
            color = hikari.Color(EMBED_COLORS["error"])
            description = f"**{bot_info['emoji']} {bot_info['label']}** beats **{player_info['emoji']} {player_info['label']}**!"
        else:
            title = "🤝 It's a draw!"
            color = hikari.Color(EMBED_COLORS["warning"])
            description = f"Both chose **{player_info['emoji']} {player_info['label']}**."

        embed = hikari.Embed(
            title=title,
            description=(
                f"You chose: {player_info['emoji']} **{player_info['label']}**\n"
                f"Bot chose: {bot_info['emoji']} **{bot_info['label']}**\n\n"
                f"{description}"
            ),
            color=color,
        )
        embed.set_footer("Run /rps to play again!")

        # Disable all buttons and update the message
        for item in self.children:
            if isinstance(item, miru.Button):
                item.disabled = True

        try:
            await self.message.edit(embed=embed, components=self)
        except Exception as exc:
            logger.error("Failed to edit RPS message: %s", exc)

        await ctx.respond(flags=hikari.MessageFlag.EPHEMERAL, content="\u200b")
        self.stop()

    @miru.button(label="Rock", emoji="🪨", style=hikari.ButtonStyle.SECONDARY, custom_id="rps_rock")
    async def rock_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        await self._handle_choice(ctx, "rock")

    @miru.button(label="Paper", emoji="📄", style=hikari.ButtonStyle.SECONDARY, custom_id="rps_paper")
    async def paper_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        await self._handle_choice(ctx, "paper")

    @miru.button(label="Scissors", emoji="✂️", style=hikari.ButtonStyle.SECONDARY, custom_id="rps_scissors")
    async def scissors_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        await self._handle_choice(ctx, "scissors")

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, miru.Button):
                item.disabled = True
        try:
            await self.message.edit(
                embed=hikari.Embed(
                    title="⏰ Timed out",
                    description="You didn't make a move in time! Run `/rps` to try again.",
                    color=hikari.Color(EMBED_COLORS["warning"]),
                ),
                components=self,
            )
        except Exception as exc:
            logger.debug("Could not update timed-out RPS message: %s", exc)
