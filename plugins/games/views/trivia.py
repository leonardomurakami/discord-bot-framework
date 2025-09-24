from __future__ import annotations

import asyncio
import html
import logging
import random
import time
from typing import Any, TYPE_CHECKING

import hikari
import miru

from ..config import games_settings, EMBED_COLORS

if TYPE_CHECKING:
    from ..plugin import GamesPlugin

logger = logging.getLogger(__name__)


class EnhancedTriviaView(miru.View):
    """Enhanced interactive trivia view with scoring, hints, and achievements."""

    def __init__(
        self,
        question_data: dict[str, Any],
        initial_embed: hikari.Embed,
        plugin: GamesPlugin,
        guild_id: int,
        is_time_attack: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # Set a longer timeout to prevent miru from timing out before our manual control
        super().__init__(timeout=games_settings.trivia_timeout_seconds + 10, *args, **kwargs)
        self.plugin = plugin
        self.guild_id = guild_id
        self.question_data = question_data
        self.participants: dict[int, tuple[str, int, float]] = {}
        self.is_finished = False
        self.initial_embed = initial_embed
        self.start_time: float | None = None
        self.trivia_message: hikari.Message | None = None
        self._countdown_task: asyncio.Task[None] | None = None
        self.is_time_attack = is_time_attack
        self.hints_given: set[int] = set()  # Track users who used hints

        # Prepare answers
        correct_answer = question_data["correct_answer"]
        all_answers = [correct_answer] + question_data["incorrect_answers"]
        random.shuffle(all_answers)

        self.correct_position = all_answers.index(correct_answer)
        self.all_answers = all_answers

        # Create answer buttons
        for i, answer in enumerate(all_answers):
            clean_answer = html.unescape(answer)
            button = miru.Button(
                style=hikari.ButtonStyle.SECONDARY,
                label=clean_answer[:80],
                custom_id=f"trivia_answer_{i}",
            )
            button.callback = self._create_answer_callback(i)
            self.add_item(button)

        # Add hint button
        hint_button = miru.Button(
            style=hikari.ButtonStyle.PRIMARY,
            label="💡 Hint",
            custom_id="trivia_hint",
            emoji="💡",
        )
        hint_button.callback = self._hint_callback
        self.add_item(hint_button)

    def start_countdown(self, message: hikari.Message | None = None) -> None:
        """Start the countdown timer."""
        if message is not None:
            self.trivia_message = message
        elif getattr(self, "message", None) is not None:
            self.trivia_message = self.message

        # Set start time if not already set
        if self.start_time is None:
            self.start_time = time.time()

        # Start countdown even without message reference initially
        # The countdown task will try to get the message reference later
        logger.debug("Starting enhanced trivia countdown")
        self._countdown_task = asyncio.create_task(self._countdown_task_impl())

    async def _countdown_task_impl(self) -> None:
        """Background task to end trivia when time runs out."""
        try:
            timeout_seconds = games_settings.trivia_timeout_seconds

            # Wait for the full timeout duration
            await asyncio.sleep(timeout_seconds)

            # Time is up - manually end the trivia
            if not self.is_finished:
                logger.debug("Countdown finished - manually ending trivia")
                await self._end_trivia()

        except asyncio.CancelledError:
            logger.debug("Countdown task was cancelled")
        except Exception as exc:
            logger.error("Countdown task error: %s", exc)


    async def _end_trivia(self) -> None:
        """Manually end the trivia and show results."""
        if self.is_finished:
            return

        logger.info("Manually ending trivia with %s participants", len(self.participants))
        await self.on_timeout()

    def _create_answer_callback(self, answer_index: int):
        """Create a callback function for the given answer index."""

        async def answer_callback(ctx: miru.ViewContext) -> None:
            if self.is_finished:
                await ctx.respond("This trivia has already ended!", flags=hikari.MessageFlag.EPHEMERAL)
                return

            if not self._countdown_task and not self.trivia_message:
                self.start_countdown()

            username = ctx.user.display_name or ctx.user.username
            answer_time = time.time()
            self.participants[ctx.user.id] = (username, answer_index, answer_time)

            chosen_answer = html.unescape(self.all_answers[answer_index])

            # Calculate response time
            if self.start_time:
                response_time = answer_time - self.start_time
                time_text = f" (answered in {response_time:.1f}s)"
            else:
                time_text = ""

            await ctx.respond(f"You chose: **{chosen_answer}**{time_text}", flags=hikari.MessageFlag.EPHEMERAL)

        return answer_callback

    async def _hint_callback(self, ctx: miru.ViewContext) -> None:
        """Handle hint button click."""
        if self.is_finished:
            await ctx.respond("This trivia has already ended!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        user_id = ctx.user.id

        # Check if user already got a hint
        if user_id in self.hints_given:
            await ctx.respond("You've already received a hint for this question!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        self.hints_given.add(user_id)

        # Remove one incorrect answer as a hint
        available_incorrect = [
            i for i, ans in enumerate(self.all_answers)
            if i != self.correct_position
        ]

        if not available_incorrect:
            await ctx.respond("No hints available for this question!", flags=hikari.MessageFlag.EPHEMERAL)
            return

        eliminated_index = random.choice(available_incorrect)
        eliminated_answer = html.unescape(self.all_answers[eliminated_index])

        hint_text = (
            f"💡 **Hint:** The answer is NOT **{eliminated_answer}**\n\n"
            f"⚠️ *Using a hint reduces your points by {int((1 - games_settings.trivia_hint_penalty) * 100)}%*"
        )

        await ctx.respond(hint_text, flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        """Handle timeout and show results with scoring."""
        if self.is_finished:
            return

        self.is_finished = True
        logger.info("Enhanced trivia timeout reached with %s participants", len(self.participants))

        correct_answer = html.unescape(self.question_data["correct_answer"])
        question_text = html.unescape(self.question_data["question"])
        difficulty = self.question_data.get("difficulty", "medium")

        embed = hikari.Embed(
            title="⏰ Trivia Results!",
            description=f"**Question:** {question_text}\n\n**Correct Answer:** {correct_answer}",
            color=hikari.Color(EMBED_COLORS["trivia"]),
        )

        if not self.participants:
            embed.add_field("Participants", "No one participated! 😢", inline=False)
        else:
            # Process participants and award points
            answer_groups: dict[int, list[tuple[str, float, int]]] = {}
            correct_participants: list[tuple[str, float, int]] = []

            for user_id, (username, answer_index, timestamp) in self.participants.items():
                answer_groups.setdefault(answer_index, []).append((username, timestamp, user_id))

                if answer_index == self.correct_position:
                    correct_participants.append((username, timestamp, user_id))

            # Award points to correct participants
            for username, timestamp, user_id in correct_participants:
                await self._award_points(user_id, self.guild_id, difficulty, timestamp, user_id in self.hints_given)

            # Display results by answer
            for answer_index, participants in answer_groups.items():
                answer_text = html.unescape(self.all_answers[answer_index])
                is_correct = answer_index == self.correct_position

                participants.sort(key=lambda item: item[1])

                participant_list = []
                for position, (username, _, user_id) in enumerate(participants):
                    medal = ""
                    if is_correct:
                        if position == 0:
                            medal = "🥇 "
                        elif position == 1:
                            medal = "🥈 "
                        elif position == 2:
                            medal = "🥉 "

                    hint_marker = " 💡" if user_id in self.hints_given else ""
                    participant_list.append(f"{medal}{username}{hint_marker}")

                emoji = "✅" if is_correct else "❌"
                field_name = f"{emoji} {answer_text}"
                field_value = "\n".join(participant_list) if participant_list else "No one"

                embed.add_field(field_name, field_value, inline=True)

            # Summary
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

            if self.is_time_attack:
                summary_value += f"\n⚡ **Time Attack Question!**"

            embed.add_field("📊 Summary", summary_value, inline=False)

        # Update button styles
        for item in self.children:
            if isinstance(item, miru.Button) and item.custom_id.startswith("trivia_answer_"):
                item.disabled = True
                button_index = int(item.custom_id.split("_")[-1])

                if button_index == self.correct_position:
                    item.style = hikari.ButtonStyle.SUCCESS
                    item.label = f"✅ {item.label}"
                else:
                    item.style = hikari.ButtonStyle.DANGER
                    item.label = f"❌ {item.label}"
            elif isinstance(item, miru.Button) and item.custom_id == "trivia_hint":
                item.disabled = True
                item.style = hikari.ButtonStyle.SECONDARY

        # Update message - try multiple methods to get message reference
        message_to_edit = None

        # Try various ways to get the message reference
        for attr_name in ["message", "_message", "trivia_message", "from_message"]:
            msg = getattr(self, attr_name, None)
            logger.debug(f"Checking {attr_name}: {type(msg)} = {msg}")
            if msg is not None:
                message_to_edit = msg
                logger.debug(f"Found message reference via {attr_name}: {type(msg)}")
                break

        if message_to_edit:
            try:
                if hasattr(message_to_edit, 'edit'):
                    await message_to_edit.edit(embed=embed, components=self)
                    logger.info("Successfully updated trivia results with enhanced features")
                else:
                    logger.error(f"Message object {type(message_to_edit)} does not have edit method")
            except Exception as exc:
                logger.error("Failed to update trivia results: %s", exc)
        else:
            logger.error("No message reference available to display trivia results! Available attributes: %s",
                        [attr for attr in dir(self) if 'message' in attr.lower()])

        if self._countdown_task and not self._countdown_task.done():
            self._countdown_task.cancel()

        self.stop()

    async def _award_points(self, user_id: int, guild_id: int | None, difficulty: str, answer_time: float, used_hint: bool) -> None:
        """Award points to a user for correct answer."""
        try:
            if not guild_id:
                logger.warning("Cannot award points - no guild_id available")
                return

            # Calculate base points
            base_points = games_settings.trivia_base_points.get(difficulty, 20)

            # Apply hint penalty
            if used_hint:
                base_points = int(base_points * games_settings.trivia_hint_penalty)

            # Time bonus for time attack questions
            if self.is_time_attack and self.start_time:
                response_time = answer_time - self.start_time
                if response_time <= games_settings.trivia_time_bonus_threshold:
                    base_points = int(base_points * games_settings.trivia_time_bonus_multiplier)

            await self.plugin.award_points(user_id, guild_id, base_points, difficulty, used_hint, answer_time - (self.start_time or 0))

        except Exception as exc:
            logger.error("Error awarding points: %s", exc)