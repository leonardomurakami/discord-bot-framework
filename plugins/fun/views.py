from __future__ import annotations

import asyncio
import html
import logging
import random
import time
from typing import Any

import hikari
import miru

from .config import fun_settings


logger = logging.getLogger(__name__)


class TriviaView(miru.View):
    """Interactive trivia view with answer buttons for multiple users."""

    def __init__(self, question_data: dict[str, Any], initial_embed: hikari.Embed, *args: Any, **kwargs: Any) -> None:
        super().__init__(timeout=fun_settings.game_view_timeout_seconds, *args, **kwargs)
        self.question_data = question_data
        self.participants: dict[int, tuple[str, int, float]] = {}
        self.is_finished = False
        self.initial_embed = initial_embed
        self.start_time: float | None = None
        self.trivia_message: hikari.Message | None = None
        self._countdown_task: asyncio.Task[None] | None = None

        # Prepare answers
        correct_answer = question_data["correct_answer"]
        all_answers = [correct_answer] + question_data["incorrect_answers"]
        random.shuffle(all_answers)

        self.correct_position = all_answers.index(correct_answer)
        self.all_answers = all_answers

        # Create buttons for each answer (all same style initially)
        for i, answer in enumerate(all_answers):
            clean_answer = html.unescape(answer)
            button = miru.Button(
                style=hikari.ButtonStyle.SECONDARY,
                label=clean_answer[:80],
                custom_id=f"trivia_answer_{i}",
            )
            button.callback = self._create_answer_callback(i)
            self.add_item(button)

    def start_countdown(self, message: hikari.Message | None = None) -> None:
        """Start the countdown timer."""
        if message is not None:
            self.trivia_message = message
        elif getattr(self, "message", None) is not None:
            self.trivia_message = self.message

        if not self.trivia_message:
            logger.warning("Cannot start countdown - no message reference available")
            return

        self.start_time = time.time()
        logger.debug("Starting trivia countdown")
        self._countdown_task = asyncio.create_task(self._countdown_task_impl())

    async def _countdown_task_impl(self) -> None:
        """Background task to update the timer."""
        try:
            # Update every 5 seconds: 25s, 20s, 15s, 10s, 5s
            for remaining in [25, 20, 15, 10, 5]:
                if self.is_finished:
                    return

                await asyncio.sleep(5)

                if self.is_finished:
                    return

                updated_embed = hikari.Embed(
                    title=self.initial_embed.title,
                    description=self.initial_embed.description,
                    color=self.initial_embed.color,
                )

                participant_count = len(self.participants)
                timer_text = f"⏱️ {remaining}s remaining"
                if participant_count > 0:
                    timer_text += f" • {participant_count} participant{'s' if participant_count != 1 else ''}"

                updated_embed.set_footer(timer_text)

                message_to_edit = self.trivia_message or getattr(self, "message", None) or getattr(self, "_message", None)

                if message_to_edit:
                    try:
                        await message_to_edit.edit(embed=updated_embed, components=self)
                    except Exception as exc:  # mirror original behaviour
                        logger.debug("Failed to update countdown: %s", exc)
                        return

        except asyncio.CancelledError:
            logger.debug("Countdown task was cancelled")
        except Exception as exc:  # unexpected error
            logger.error("Countdown task error: %s", exc)

    def _create_answer_callback(self, answer_index: int):
        """Create a callback function for the given answer index."""

        async def answer_callback(ctx: miru.ViewContext) -> None:
            if self.is_finished:
                await ctx.respond("This trivia has already ended!", flags=hikari.MessageFlag.EPHEMERAL)
                return

            if not self._countdown_task and not self.trivia_message:
                self.start_countdown()

            username = ctx.user.display_name or ctx.user.username
            self.participants[ctx.user.id] = (username, answer_index, time.time())

            chosen_answer = html.unescape(self.all_answers[answer_index])
            await ctx.respond(f"You chose: **{chosen_answer}**", flags=hikari.MessageFlag.EPHEMERAL)

        return answer_callback

    async def on_timeout(self) -> None:
        """Handle timeout and show results."""
        if self.is_finished:
            return

        self.is_finished = True
        logger.info("Trivia timeout reached with %s participants", len(self.participants))

        correct_answer = html.unescape(self.question_data["correct_answer"])
        question_text = html.unescape(self.question_data["question"])

        embed = hikari.Embed(
            title="⏰ Trivia Results!",
            description=f"**Question:** {question_text}\n\n**Correct Answer:** {correct_answer}",
            color=hikari.Color(0x9932CC),
        )

        if not self.participants:
            embed.add_field("Participants", "No one participated! 😢", inline=False)
        else:
            answer_groups: dict[int, list[tuple[str, float]]] = {}
            correct_participants: list[tuple[str, float]] = []

            for username, answer_index, timestamp in self.participants.values():
                answer_groups.setdefault(answer_index, []).append((username, timestamp))
                if answer_index == self.correct_position:
                    correct_participants.append((username, timestamp))

            for answer_index, participants in answer_groups.items():
                answer_text = html.unescape(self.all_answers[answer_index])
                is_correct = answer_index == self.correct_position

                participants.sort(key=lambda item: item[1])

                participant_list = []
                for position, (username, _) in enumerate(participants):
                    medal = ""
                    if is_correct:
                        if position == 0:
                            medal = "🥇 "
                        elif position == 1:
                            medal = "🥈 "
                        elif position == 2:
                            medal = "🥉 "

                    participant_list.append(f"{medal}{username}")

                emoji = "✅" if is_correct else "❌"
                field_name = f"{emoji} {answer_text}"
                field_value = "\n".join(participant_list) if participant_list else "No one"

                embed.add_field(field_name, field_value, inline=True)

            total_participants = len(self.participants)
            correct_count = len(correct_participants)

            if correct_count > 0:
                correct_participants.sort(key=lambda item: item[1])
                fastest_correct = correct_participants[0][0]

                summary_value = (
                    f"**Total Participants:** {total_participants}\n"
                    f"**Correct Answers:** {correct_count}\n"
                    f"**Fastest Correct:** {fastest_correct}"
                )
            else:
                summary_value = (
                    f"**Total Participants:** {total_participants}\n"
                    "**Correct Answers:** 0\n"
                    "Everyone got it wrong! 😅"
                )

            embed.add_field("📊 Summary", summary_value, inline=False)

        for item in self.children:
            if isinstance(item, miru.Button):
                item.disabled = True
                button_index = int(item.custom_id.split("_")[-1])

                if button_index == self.correct_position:
                    item.style = hikari.ButtonStyle.SUCCESS
                    item.label = f"✅ {item.label}"
                else:
                    item.style = hikari.ButtonStyle.DANGER
                    item.label = f"❌ {item.label}"

        message_to_edit = self.trivia_message or getattr(self, "message", None) or getattr(self, "_message", None)

        if message_to_edit:
            try:
                await message_to_edit.edit(embed=embed, components=self)
                logger.info("Successfully updated trivia results with buttons")
            except (hikari.NotFoundError, hikari.ForbiddenError, hikari.HTTPError) as exc:
                logger.warning("Failed to update trivia message: %s", exc)
                try:
                    await message_to_edit.edit(embed=embed)
                    logger.info("Successfully updated trivia results without buttons")
                except Exception as second_exc:
                    logger.error("Failed to update trivia results completely: %s", second_exc)
            except Exception as exc:
                logger.error("Unexpected error updating trivia results: %s", exc)
        else:
            logger.error("No message reference found for trivia results update")

        if self._countdown_task and not self._countdown_task.done():
            self._countdown_task.cancel()

        self.stop()


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

