"""Interactive views for the daily Angle guessing game."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import hikari
import miru

from ..config import ANGLE_MAX_ATTEMPTS, ANGLE_POINTS, EMBED_COLORS
from ..utils.angle_image import generate_angle_image

if TYPE_CHECKING:
    from ..plugin import GamesPlugin

logger = logging.getLogger(__name__)

# Colour used for each attempt row in the embed (same palette as the image rays)
_ATTEMPT_COLORS = ["🟡", "🟣", "🔴", "🟢"]


def _build_angle_embed(plugin: GamesPlugin, state: dict[str, Any], user_mention: str) -> hikari.Embed:
    """Build the embed showing current game progress."""
    guesses = state["guesses"]
    target = state["target"]
    is_complete = state["is_complete"]
    won = state["won"]
    attempts_remaining = state["attempts_remaining"]
    points_eligible = state["points_eligible"]

    if is_complete and won:
        title = "🎉 You got it!"
        color = hikari.Color(0x57F287)  # green
    elif is_complete and not won:
        title = "💀 Out of attempts!"
        color = hikari.Color(EMBED_COLORS["error"])
    else:
        title = "📐 Angle — Daily Challenge"
        color = hikari.Color(EMBED_COLORS["angle"])

    embed = hikari.Embed(title=title, color=color)

    # --- guess history ---
    history_lines: list[str] = []
    for i, guess in enumerate(guesses):
        dist = plugin.angle_distance(guess, target)
        direction = plugin.angle_direction(guess, target)
        color_dot = _ATTEMPT_COLORS[i % len(_ATTEMPT_COLORS)]

        if dist == 0:
            feedback = "✅ **Exact!**"
        elif dist == 1:
            arrow = "⬆️" if direction == "higher" else "⬇️"
            feedback = f"{arrow} **{dist}° off** — go {direction}"
        elif dist == 2:
            arrow = "⬆️" if direction == "higher" else "⬇️"
            feedback = f"{arrow} **{dist}° off** — go {direction}"
        else:
            arrow = "⬆️" if direction == "higher" else "⬇️"
            feedback = f"{arrow} {dist}° off — go {direction}"

        history_lines.append(f"{color_dot} Guess #{i + 1}: **{guess}°** — {feedback}")

    if history_lines:
        embed.add_field("Your Guesses", "\n".join(history_lines), inline=False)
    else:
        embed.description = (
            f"{user_mention} — guess the daily angle! (0–360°)\n"
            "You get **4 attempts**. After each guess you'll see how far off you are.\n\n"
            "*Inspired by [angle.wtf](https://angle.wtf)*"
        )

    # --- result / status ---
    if is_complete:
        if won:
            pts = state["points_awarded"]
            dist_final = plugin.angle_distance(guesses[-1], target)
            if dist_final == 0:
                quality = "Perfect! 💯"
            elif dist_final <= 2:
                quality = "Very close! 🎯"
            else:
                quality = "Nice guess! 👍"
            points_note = f"+**{pts}** points" if points_eligible and pts > 0 else "(no points — already played today)"
            embed.add_field("Result", f"The angle was **{target}°**\n{quality}\n{points_note}", inline=False)
        else:
            embed.add_field("Result", f"The angle was **{target}°**\nBetter luck tomorrow!", inline=False)
    else:
        remaining_text = f"{attempts_remaining} attempt(s) remaining"
        if not points_eligible:
            remaining_text += " *(no points — already played today)*"
        embed.set_footer(remaining_text)

    embed.set_image("attachment://angle.png")
    return embed


class AngleGuessModal(miru.Modal, title="Guess the Angle"):
    """Modal that prompts the user to enter their angle guess."""

    angle_input: miru.TextInput = miru.TextInput(
        label="Your guess (0–360 degrees)",
        placeholder="e.g. 45",
        required=True,
        max_length=3,
    )

    def __init__(self, plugin: GamesPlugin, user_id: int, guild_id: int, view: AngleView) -> None:
        super().__init__()
        self.plugin = plugin
        self.user_id = user_id
        self.guild_id = guild_id
        self.angle_view = view

    async def callback(self, ctx: miru.ModalContext) -> None:
        raw = (self.angle_input.value or "").strip()
        try:
            guess = int(raw)
            if not 0 <= guess <= 360:
                raise ValueError
        except ValueError:
            await ctx.respond(
                "Please enter a whole number between 0 and 360.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return

        try:
            state = await self.plugin.process_angle_guess(self.user_id, self.guild_id, guess)
        except Exception as exc:
            logger.error("Error processing angle guess: %s", exc)
            await ctx.respond("Something went wrong. Please try again.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        is_complete = state.get("is_complete", False)

        # Generate image (reveal target only when game over)
        target_reveal = state["target"] if is_complete else None
        image_bytes = generate_angle_image(state["guesses"], target=target_reveal)

        user_mention = f"<@{self.user_id}>"
        embed = _build_angle_embed(self.plugin, state, user_mention)

        # Build the updated view (remove button if game over)
        new_view: AngleView | None = None
        if not is_complete:
            new_view = AngleView(self.plugin, self.user_id, self.guild_id, state)

        attachment = hikari.Bytes(image_bytes, "angle.png")

        try:
            if new_view:
                await self.angle_view.message.edit(
                    embed=embed,
                    attachments=[attachment],
                    components=new_view,
                )
                # Re-bind the new view so its button works
                miru_client = getattr(self.plugin.bot, "miru_client", None)
                if miru_client:
                    miru_client.start_view(new_view, bind_to=self.angle_view.message)
            else:
                await self.angle_view.message.edit(
                    embed=embed,
                    attachments=[attachment],
                    components=[],
                )
            # Acknowledge the modal interaction silently
            await ctx.respond(flags=hikari.MessageFlag.EPHEMERAL, content="\u200b")
        except Exception as exc:
            logger.error("Failed to update angle message: %s", exc)
            await ctx.respond("Guess recorded! Run `/angle` to see your updated board.", flags=hikari.MessageFlag.EPHEMERAL)


class AngleView(miru.View):
    """Persistent view with a single 'Make Guess' button for the angle game."""

    def __init__(
        self,
        plugin: GamesPlugin,
        user_id: int,
        guild_id: int,
        state: dict[str, Any],
    ) -> None:
        super().__init__(timeout=300)
        self.plugin = plugin
        self.user_id = user_id
        self.guild_id = guild_id
        self.state = state

    @miru.button(label="🎯 Make Guess", style=hikari.ButtonStyle.PRIMARY, custom_id="angle_guess")
    async def guess_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        # Only the player who started the game can guess
        if ctx.user.id != self.user_id:
            await ctx.respond(
                "This is not your game! Run `/angle` to start your own.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return

        if self.state.get("is_complete"):
            await ctx.respond("Your game for today is already finished!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if self.state.get("attempts_remaining", 0) <= 0:
            await ctx.respond("You have no attempts remaining!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        modal = AngleGuessModal(self.plugin, self.user_id, self.guild_id, self)
        await ctx.respond_with_modal(modal)
