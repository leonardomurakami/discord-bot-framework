import logging
import random

import aiohttp
import hikari
import lightbulb
import miru

from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command
from bot.web.mixins import WebPanelMixin
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from typing import Dict, Any

# Plugin metadata for the loader
PLUGIN_METADATA = {
    "name": "Fun",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Fun commands and games for entertainment including dice rolling, jokes, quotes, and random generators",
    "permissions": ["fun.games", "fun.images"],
}

logger = logging.getLogger(__name__)


class TriviaView(miru.View):
    """Interactive trivia view with answer buttons for multiple users."""

    def __init__(self, question_data: dict, initial_embed: hikari.Embed, *args, **kwargs):
        super().__init__(timeout=30, *args, **kwargs)
        self.question_data = question_data
        self.participants = {}  # {user_id: (username, answer_index, timestamp)}
        self.is_finished = False
        self.initial_embed = initial_embed
        self.start_time = None
        self.trivia_message = None
        self._countdown_task = None

        # Prepare answers
        correct_answer = question_data["correct_answer"]
        all_answers = [correct_answer] + question_data["incorrect_answers"]
        random.shuffle(all_answers)

        self.correct_position = all_answers.index(correct_answer)
        self.all_answers = all_answers

        # Create buttons for each answer (all same style initially)
        for i, answer in enumerate(all_answers):
            import html
            clean_answer = html.unescape(answer)
            button = miru.Button(
                style=hikari.ButtonStyle.SECONDARY,  # Single gray style for all
                label=clean_answer[:80],  # Discord button label limit
                custom_id=f"trivia_answer_{i}"
            )
            button.callback = self._create_answer_callback(i)
            self.add_item(button)

    def start_countdown(self, message=None):
        """Start the countdown timer."""
        import time
        import asyncio

        # Use provided message or try to find one
        if message:
            self.trivia_message = message
        elif hasattr(self, 'message') and self.message:
            self.trivia_message = self.message

        if not self.trivia_message:
            logger.warning("Cannot start countdown - no message reference available")
            return

        self.start_time = time.time()
        logger.debug(f"Starting countdown with message: {type(self.trivia_message)}")
        self._countdown_task = asyncio.create_task(self._countdown_task())

    async def _countdown_task(self):
        """Background task to update the timer."""
        import asyncio
        import time

        try:
            # Update every 5 seconds: 25s, 20s, 15s, 10s, 5s
            for remaining in [25, 20, 15, 10, 5]:
                if self.is_finished:
                    return

                await asyncio.sleep(5)  # Wait 5 seconds

                if self.is_finished:
                    return

                # Update embed with timer and participant count
                updated_embed = hikari.Embed(
                    title=self.initial_embed.title,
                    description=self.initial_embed.description,
                    color=self.initial_embed.color,
                )

                # Add timer and participant info
                participant_count = len(self.participants)
                timer_text = f"⏱️ {remaining}s remaining"
                if participant_count > 0:
                    timer_text += f" • {participant_count} participant{'s' if participant_count != 1 else ''}"

                updated_embed.set_footer(timer_text)

                # Try to update the message
                message_to_edit = None
                if self.trivia_message:
                    message_to_edit = self.trivia_message
                elif hasattr(self, 'message') and self.message:
                    message_to_edit = self.message
                elif hasattr(self, '_message') and self._message:
                    message_to_edit = self._message

                if message_to_edit:
                    try:
                        await message_to_edit.edit(embed=updated_embed, components=self)
                    except Exception as e:
                        logger.debug(f"Failed to update countdown: {e}")
                        # If message editing fails, stop the countdown
                        return

        except asyncio.CancelledError:
            logger.debug("Countdown task was cancelled")
        except Exception as e:
            logger.error(f"Countdown task error: {e}")

    def _create_answer_callback(self, answer_index: int):
        """Create a callback function for the given answer index."""
        async def answer_callback(ctx: miru.ViewContext):
            if self.is_finished:
                await ctx.respond("This trivia has already ended!", flags=hikari.MessageFlag.EPHEMERAL)
                return

            # Start countdown if not already started (fallback for when miru sets message later)
            if not self._countdown_task and not self.trivia_message:
                self.start_countdown()

            # Record user's answer (they can change it)
            import time
            username = ctx.user.display_name or ctx.user.username
            self.participants[ctx.user.id] = (
                username,
                answer_index,
                time.time()
            )

            # Give feedback about their choice
            import html
            chosen_answer = html.unescape(self.all_answers[answer_index])
            await ctx.respond(f"You chose: **{chosen_answer}**", flags=hikari.MessageFlag.EPHEMERAL)

        return answer_callback

    async def on_timeout(self) -> None:
        """Handle timeout and show results."""
        if self.is_finished:
            return  # Already processed

        self.is_finished = True
        logger.info(f"Trivia timeout reached with {len(self.participants)} participants")

        import html
        correct_answer = html.unescape(self.question_data["correct_answer"])
        question_text = html.unescape(self.question_data["question"])

        # Create results embed
        embed = hikari.Embed(
            title="⏰ Trivia Results!",
            description=f"**Question:** {question_text}\n\n**Correct Answer:** {correct_answer}",
            color=hikari.Color(0x9932CC),
        )

        if not self.participants:
            embed.add_field("Participants", "No one participated! 😢", inline=False)
        else:
            # Group participants by their answers
            answer_groups = {}
            correct_participants = []

            for user_id, (username, answer_index, timestamp) in self.participants.items():
                answer_text = html.unescape(self.all_answers[answer_index])

                if answer_index not in answer_groups:
                    answer_groups[answer_index] = []
                answer_groups[answer_index].append((username, timestamp))

                if answer_index == self.correct_position:
                    correct_participants.append((username, timestamp))

            # Show results for each answer
            for answer_index, participants in answer_groups.items():
                answer_text = html.unescape(self.all_answers[answer_index])
                is_correct = answer_index == self.correct_position

                # Sort by timestamp (first to answer first)
                participants.sort(key=lambda x: x[1])

                participant_list = []
                for i, (username, timestamp) in enumerate(participants):
                    medal = ""
                    if is_correct:
                        if i == 0:
                            medal = "🥇 "  # First correct
                        elif i == 1:
                            medal = "🥈 "  # Second correct
                        elif i == 2:
                            medal = "🥉 "  # Third correct

                    participant_list.append(f"{medal}{username}")

                emoji = "✅" if is_correct else "❌"
                field_name = f"{emoji} {answer_text}"
                field_value = "\n".join(participant_list) if participant_list else "No one"

                embed.add_field(field_name, field_value, inline=True)

            # Add summary
            total_participants = len(self.participants)
            correct_count = len(correct_participants)

            if correct_count > 0:
                # Sort correct participants by timestamp
                correct_participants.sort(key=lambda x: x[1])
                fastest_correct = correct_participants[0][0]

                embed.add_field(
                    "📊 Summary",
                    f"**Total Participants:** {total_participants}\n"
                    f"**Correct Answers:** {correct_count}\n"
                    f"**Fastest Correct:** {fastest_correct}" if correct_count > 0 else f"**Correct Answers:** 0",
                    inline=False
                )
            else:
                embed.add_field(
                    "📊 Summary",
                    f"**Total Participants:** {total_participants}\n"
                    f"**Correct Answers:** 0\n"
                    f"Everyone got it wrong! 😅",
                    inline=False
                )

        # Color-code and disable all buttons
        for item in self.children:
            if isinstance(item, miru.Button):
                item.disabled = True
                button_index = int(item.custom_id.split('_')[-1])

                if button_index == self.correct_position:
                    # Correct answer - green
                    item.style = hikari.ButtonStyle.SUCCESS
                    item.label = f"✅ {item.label}"
                else:
                    # Wrong answer - red
                    item.style = hikari.ButtonStyle.DANGER
                    item.label = f"❌ {item.label}"

        # Update the message with results - try multiple message sources
        message_to_edit = None

        # Try different ways to get the message reference
        if self.trivia_message:
            message_to_edit = self.trivia_message
            logger.debug("Using trivia_message")
        elif hasattr(self, 'message') and self.message:
            message_to_edit = self.message
            logger.debug("Using self.message")
        elif hasattr(self, '_message') and self._message:
            message_to_edit = self._message
            logger.debug("Using self._message")

        if message_to_edit:
            try:
                await message_to_edit.edit(embed=embed, components=self)
                logger.info("Successfully updated trivia results with buttons")
            except (hikari.NotFoundError, hikari.ForbiddenError, hikari.HTTPError) as e:
                logger.warning(f"Failed to update trivia message: {e}")
                # Try without components if edit fails
                try:
                    await message_to_edit.edit(embed=embed)
                    logger.info("Successfully updated trivia results without buttons")
                except Exception as e2:
                    logger.error(f"Failed to update trivia results completely: {e2}")
            except Exception as e:
                logger.error(f"Unexpected error updating trivia results: {e}")
        else:
            logger.error(f"No message reference found. trivia_message: {self.trivia_message}, hasattr message: {hasattr(self, 'message')}, hasattr _message: {hasattr(self, '_message')}")

        # Cancel the countdown task if it's running
        if self._countdown_task and not self._countdown_task.done():
            self._countdown_task.cancel()

        # Stop the view to prevent further interactions
        self.stop()


class WouldYouRatherView(miru.View):
    """Interactive would you rather view with voting buttons."""

    def __init__(self, option_a: str, option_b: str, *args, **kwargs):
        super().__init__(timeout=300, *args, **kwargs)  # 5 minutes
        self.option_a = option_a
        self.option_b = option_b
        self.votes_a = set()
        self.votes_b = set()

        # Create voting buttons
        button_a = miru.Button(
            style=hikari.ButtonStyle.PRIMARY,
            label="Option A",
            emoji="🅰️",
            custom_id="wyr_option_a"
        )
        button_a.callback = self.vote_option_a
        self.add_item(button_a)

        button_b = miru.Button(
            style=hikari.ButtonStyle.SECONDARY,
            label="Option B",
            emoji="🅱️",
            custom_id="wyr_option_b"
        )
        button_b.callback = self.vote_option_b
        self.add_item(button_b)

    async def vote_option_a(self, ctx: miru.ViewContext):
        """Handle vote for option A."""
        user_id = ctx.user.id

        # Remove from B if they were there
        self.votes_b.discard(user_id)

        # Toggle vote for A
        if user_id in self.votes_a:
            self.votes_a.discard(user_id)
            await ctx.respond("Removed your vote for Option A!", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            self.votes_a.add(user_id)
            await ctx.respond("Voted for Option A!", flags=hikari.MessageFlag.EPHEMERAL)

        await self._update_results(ctx)

    async def vote_option_b(self, ctx: miru.ViewContext):
        """Handle vote for option B."""
        user_id = ctx.user.id

        # Remove from A if they were there
        self.votes_a.discard(user_id)

        # Toggle vote for B
        if user_id in self.votes_b:
            self.votes_b.discard(user_id)
            await ctx.respond("Removed your vote for Option B!", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            self.votes_b.add(user_id)
            await ctx.respond("Voted for Option B!", flags=hikari.MessageFlag.EPHEMERAL)

        await self._update_results(ctx)

    async def _update_results(self, ctx: miru.ViewContext):
        """Update the embed with current voting results."""
        total_votes = len(self.votes_a) + len(self.votes_b)

        if total_votes == 0:
            percent_a = percent_b = 0
        else:
            percent_a = (len(self.votes_a) / total_votes) * 100
            percent_b = (len(self.votes_b) / total_votes) * 100

        # Create progress bars
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
            inline=True
        )

        embed.add_field(
            "🅱️ Option B",
            f"{self.option_b}\n\n{bar_b} {len(self.votes_b)} votes ({percent_b:.1f}%)",
            inline=True
        )

        embed.set_footer(f"Total votes: {total_votes} • Click buttons to vote!")

        try:
            await ctx.edit_response(embed=embed, components=self)
        except:
            pass  # Ignore edit failures


class FunPlugin(BasePlugin, WebPanelMixin):
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession = None

    async def on_load(self) -> None:
        self.session = aiohttp.ClientSession()
        await super().on_load()

    async def on_unload(self) -> None:
        if self.session:
            await self.session.close()
        await super().on_unload()

    @command(name="ping", description="Test command - check if bot is responding")
    async def ping_command(self, ctx) -> None:
        try:
            logger.info(f"Ping command called by {ctx.author.username}")
            embed = self.create_embed(
                title="🏓 Pong!",
                description="Bot is working correctly!",
                color=hikari.Color(0x00FF00),
            )
            await ctx.respond(embed=embed)
            logger.info("Ping command responded successfully")
        except Exception as e:
            logger.error(f"Error in ping command: {e}")

    @command(
        name="roll",
        description="Roll dice (format: NdN, e.g., 2d6)",
        aliases=["r"],
        permission_node="fun.games",
        arguments=[
            CommandArgument(
                "dice",
                hikari.OptionType.STRING,
                "Dice notation (e.g., 1d6, 2d20)",
                required=False,
                default="1d6",
            )
        ],
    )
    async def roll_dice(self, ctx: lightbulb.Context, dice: str = "1d6") -> None:
        try:
            # Parse dice notation
            if "d" not in dice.lower():
                embed = self.create_embed(
                    title="❌ Invalid Format",
                    description="Please use dice notation like `1d6`, `2d20`, etc.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            parts = dice.lower().split("d")
            if len(parts) != 2:
                raise ValueError("Invalid dice format")

            num_dice = int(parts[0]) if parts[0] else 1
            num_sides = int(parts[1])

            if num_dice < 1 or num_dice > 20:
                embed = self.create_embed(
                    title="❌ Invalid Range",
                    description="Number of dice must be between 1 and 20.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if num_sides < 2 or num_sides > 1000:
                embed = self.create_embed(
                    title="❌ Invalid Range",
                    description="Number of sides must be between 2 and 1000.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Roll the dice
            rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
            total = sum(rolls)

            # Create result
            if num_dice == 1:
                result_text = f"🎲 You rolled a **{total}**!"
            else:
                rolls_text = ", ".join(str(roll) for roll in rolls)
                result_text = f"🎲 You rolled: {rolls_text}\nTotal: **{total}**"

            embed = self.create_embed(
                title=f"Dice Roll ({dice})",
                description=result_text,
                color=hikari.Color(0x00FF00),
            )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "roll", True)

        except ValueError:
            embed = self.create_embed(
                title="❌ Invalid Format",
                description="Please use valid dice notation like `1d6`, `2d20`, etc.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "roll", False, "Invalid format")

        except Exception as e:
            logger.error(f"Error in roll command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "roll", False, str(e))

    @command(name="coinflip", description="Flip a coin", permission_node="fun.games")
    async def flip_coin(self, ctx: lightbulb.Context) -> None:
        try:
            result = random.choice(["Heads", "Tails"])
            emoji = "🪙" if result == "Heads" else "🪙"

            embed = self.create_embed(
                title="Coin Flip",
                description=f"{emoji} The coin landed on **{result}**!",
                color=hikari.Color(0xFFD700),
            )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "coinflip", True)

        except Exception as e:
            logger.error(f"Error in coinflip command: {e}")
            await self.log_command_usage(ctx, "coinflip", False, str(e))

    @command(
        name="8ball",
        description="Ask the magic 8-ball a question",
        permission_node="fun.games",
        arguments=[CommandArgument("question", hikari.OptionType.STRING, "Your question for the 8-ball")],
    )
    async def magic_8ball(self, ctx: lightbulb.Context, question: str) -> None:
        try:
            responses = [
                "It is certain",
                "It is decidedly so",
                "Without a doubt",
                "Yes definitely",
                "You may rely on it",
                "As I see it, yes",
                "Most likely",
                "Outlook good",
                "Yes",
                "Signs point to yes",
                "Reply hazy, try again",
                "Ask again later",
                "Better not tell you now",
                "Cannot predict now",
                "Concentrate and ask again",
                "Don't count on it",
                "My reply is no",
                "My sources say no",
                "Outlook not so good",
                "Very doubtful",
            ]

            response = random.choice(responses)

            embed = self.create_embed(
                title="🎱 Magic 8-Ball",
                description=f"**Question:** {question}\n**Answer:** {response}",
                color=hikari.Color(0x8B00FF),
            )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "8ball", True)

        except Exception as e:
            logger.error(f"Error in 8ball command: {e}")
            await self.log_command_usage(ctx, "8ball", False, str(e))

    @command(name="joke", description="Get a random joke")
    async def random_joke(self, ctx: lightbulb.Context) -> None:
        try:
            if not self.session:
                embed = self.create_embed(
                    title="❌ Service Unavailable",
                    description="Joke service is currently unavailable.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Try to fetch from joke API
            try:
                async with self.session.get(
                    "https://v2.jokeapi.dev/joke/Programming,Miscellaneous?blacklistFlags=nsfw,religious,political,racist,sexist,explicit"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        if data["type"] == "single":
                            joke_text = data["joke"]
                        else:
                            joke_text = f"{data['setup']}\n\n{data['delivery']}"

                        embed = self.create_embed(
                            title="😂 Random Joke",
                            description=joke_text,
                            color=hikari.Color(0xFFD700),
                        )
                    else:
                        raise Exception("API request failed")

            except Exception:
                # Fallback to local jokes
                local_jokes = [
                    "Why don't scientists trust atoms? Because they make up everything!",
                    "Why did the scarecrow win an award? He was outstanding in his field!",
                    "Why don't eggs tell jokes? They'd crack each other up!",
                    "What do you call a fake noodle? An impasta!",
                    "Why did the math book look so sad? Because it was full of problems!",
                ]

                joke_text = random.choice(local_jokes)
                embed = self.create_embed(
                    title="😂 Random Joke",
                    description=joke_text,
                    color=hikari.Color(0xFFD700),
                )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "joke", True)

        except Exception as e:
            logger.error(f"Error in joke command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to get a joke. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "joke", False, str(e))

    @command(
        name="choose",
        description="Let the bot choose between options",
        arguments=[
            CommandArgument("option1", hikari.OptionType.STRING, "Option 1"),
            CommandArgument("option2", hikari.OptionType.STRING, "Option 2"),
        ],
    )
    async def choose_option(self, ctx: lightbulb.Context, option1: str, option2: str) -> None:
        try:
            # Split and clean options
            choices = [option1, option2]

            if len(choices) < 2:
                embed = self.create_embed(
                    title="❌ Not Enough Options",
                    description="Please provide at least 2 options.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            chosen = random.choice(choices)

            embed = self.create_embed(
                title="🤔 Choice Made",
                description=f"I choose: **{chosen}**",
                color=hikari.Color(0x00FF00),
            )

            # Add all options as a field
            options_text = "\n".join([f"• {choice}" for choice in choices])
            embed.add_field("Options", options_text, inline=False)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "choose", True)

        except Exception as e:
            logger.error(f"Error in choose command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "choose", False, str(e))

    @command(
        name="random",
        description="Generate random numbers within a range",
        aliases=["rng", "rand"],
        permission_node="fun.games",
        arguments=[
            CommandArgument(
                "min_value",
                hikari.OptionType.INTEGER,
                "Minimum value (default: 1)",
                required=False,
                default=1,
            ),
            CommandArgument(
                "max_value",
                hikari.OptionType.INTEGER,
                "Maximum value (default: 100)",
                required=False,
                default=100,
            ),
        ],
    )
    async def random_number(self, ctx: lightbulb.Context, min_value: int = 1, max_value: int = 100) -> None:
        try:
            # Validate input
            if min_value > max_value:
                embed = self.create_embed(
                    title="❌ Invalid Range",
                    description="Minimum value cannot be greater than maximum value.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Prevent extremely large ranges
            if abs(max_value - min_value) > 10_000_000:
                embed = self.create_embed(
                    title="❌ Range Too Large",
                    description="Range cannot exceed 10 million numbers.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Generate random number
            result = random.randint(min_value, max_value)

            embed = self.create_embed(
                title="🎲 Random Number",
                description=f"🎯 Generated: **{result}**",
                color=hikari.Color(0x9932CC),
            )

            embed.add_field("Range", f"{min_value} - {max_value}", inline=True)
            embed.add_field("Total Possibilities", str(max_value - min_value + 1), inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "random", True)

        except Exception as e:
            logger.error(f"Error in random command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "random", False, str(e))

    @command(
        name="quote",
        description="Get a random inspirational quote",
        aliases=["inspire", "wisdom"],
    )
    async def random_quote(self, ctx: lightbulb.Context) -> None:
        try:
            # Try to fetch from online API first
            quote_text = None
            quote_author = None

            if self.session:
                try:
                    async with self.session.get("https://api.quotable.io/random?maxLength=150") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            quote_text = data.get("content")
                            quote_author = data.get("author")
                except Exception:
                    pass  # Fall back to local quotes

            # Fallback to local quotes if API fails
            if not quote_text:
                local_quotes = [
                    (
                        "The only way to do great work is to love what you do.",
                        "Steve Jobs",
                    ),
                    (
                        "Innovation distinguishes between a leader and a follower.",
                        "Steve Jobs",
                    ),
                    (
                        "Life is what happens to you while you're busy making other plans.",
                        "John Lennon",
                    ),
                    (
                        "The future belongs to those who believe in the beauty of their dreams.",
                        "Eleanor Roosevelt",
                    ),
                    (
                        "It is during our darkest moments that we must focus to see the light.",
                        "Aristotle",
                    ),
                    (
                        "Success is not final, failure is not fatal: it is the courage to continue that counts.",
                        "Winston Churchill",
                    ),
                    (
                        "The only impossible journey is the one you never begin.",
                        "Tony Robbins",
                    ),
                    (
                        "In the middle of difficulty lies opportunity.",
                        "Albert Einstein",
                    ),
                    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
                    (
                        "The only limit to our realization of tomorrow will be our doubts of today.",
                        "Franklin D. Roosevelt",
                    ),
                    (
                        "Do not go where the path may lead, go instead where there is no path and leave a trail.",
                        "Ralph Waldo Emerson",
                    ),
                    (
                        "The way to get started is to quit talking and begin doing.",
                        "Walt Disney",
                    ),
                    (
                        "Don't be afraid to give up the good to go for the great.",
                        "John D. Rockefeller",
                    ),
                    (
                        "If you really look closely, most overnight successes took a long time.",
                        "Steve Jobs",
                    ),
                    (
                        "The greatest glory in living lies not in never falling, but in rising every time we fall.",
                        "Nelson Mandela",
                    ),
                ]

                quote_text, quote_author = random.choice(local_quotes)

            embed = self.create_embed(
                title="💭 Inspirational Quote",
                description=f'*"{quote_text}"*',
                color=hikari.Color(0x8A2BE2),
            )

            if quote_author:
                embed.add_field("Author", f"— {quote_author}", inline=False)

            # Add a random motivational emoji
            motivational_emojis = ["💪", "🌟", "✨", "🎯", "🚀", "💎", "🔥", "⭐"]
            emoji = random.choice(motivational_emojis)
            embed.set_footer(f"{emoji} Stay inspired!")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "quote", True)

        except Exception as e:
            logger.error(f"Error in quote command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to get a quote. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "quote", False, str(e))

    @command(
        name="trivia",
        description="Start an interactive trivia question",
        permission_node="fun.games",
    )
    async def trivia_question(self, ctx: lightbulb.Context) -> None:
        try:
            # Try to fetch from online trivia API
            question_data = None
            if self.session:
                try:
                    async with self.session.get("https://opentdb.com/api.php?amount=1&type=multiple") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data["response_code"] == 0 and data["results"]:
                                question_data = data["results"][0]
                except Exception:
                    pass

            # Fallback to local trivia questions
            if not question_data:
                local_trivia = [
                    {
                        "question": "What is the capital of Japan?",
                        "correct_answer": "Tokyo",
                        "incorrect_answers": ["Osaka", "Kyoto", "Hiroshima"],
                        "category": "Geography"
                    },
                    {
                        "question": "Which planet is known as the Red Planet?",
                        "correct_answer": "Mars",
                        "incorrect_answers": ["Venus", "Jupiter", "Saturn"],
                        "category": "Science"
                    },
                    {
                        "question": "Who painted the Mona Lisa?",
                        "correct_answer": "Leonardo da Vinci",
                        "incorrect_answers": ["Pablo Picasso", "Vincent van Gogh", "Michelangelo"],
                        "category": "Art"
                    },
                    {
                        "question": "What is the largest mammal in the world?",
                        "correct_answer": "Blue Whale",
                        "incorrect_answers": ["Elephant", "Giraffe", "Hippopotamus"],
                        "category": "Nature"
                    },
                    {
                        "question": "In which year did World War II end?",
                        "correct_answer": "1945",
                        "incorrect_answers": ["1944", "1946", "1943"],
                        "category": "History"
                    }
                ]
                question_data = random.choice(local_trivia)

            # Clean HTML entities from question text
            import html
            question_text = html.unescape(question_data["question"])

            embed = self.create_embed(
                title="🧠 Trivia Time!",
                description=f"**Category:** {question_data.get('category', 'General')}\n\n**Question:**\n{question_text}",
                color=hikari.Color(0x9932CC),
            )

            embed.set_footer("⏱️ 30s remaining • Click the correct answer!")

            # Create view with answer buttons
            view = TriviaView(question_data, embed)

            # Send message with view
            miru_client = getattr(self.bot, "miru_client", None)
            if miru_client:
                message = await ctx.respond(embed=embed, components=view)
                miru_client.start_view(view)

                # Get the actual message from the response (following music plugin pattern)
                if message is None:
                    # ctx.respond() sometimes returns None initially, but miru will set view.message later
                    logger.debug("ctx.respond() returned None - miru will set view.message later")
                elif hasattr(message, "message"):
                    view.trivia_message = message.message
                    view.message = message.message  # Also set the standard miru message property
                    logger.debug(f"Set trivia_message from message.message: {type(message.message)}")
                elif hasattr(message, "id"):
                    view.trivia_message = message
                    view.message = message  # Also set the standard miru message property
                    logger.debug(f"Set trivia_message from message: {type(message)}")
                else:
                    logger.warning(f"Message object has no 'message' or 'id' attribute. Type: {type(message)}")

                # Start the countdown timer with the proper message reference (if available)
                if view.trivia_message:
                    view.start_countdown(view.trivia_message)
                else:
                    logger.debug("No immediate message reference - countdown will start when miru sets view.message")
            else:
                await ctx.respond(embed=embed)

            await self.log_command_usage(ctx, "trivia", True)

        except Exception as e:
            logger.error(f"Error in trivia command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to start trivia question. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "trivia", False, str(e))

    @command(
        name="meme",
        description="Get a random meme",
        permission_node="fun.images",
    )
    async def random_meme(self, ctx: lightbulb.Context) -> None:
        try:
            if not self.session:
                embed = self.create_embed(
                    title="❌ Service Unavailable",
                    description="Meme service is currently unavailable.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Try to fetch from meme API
            try:
                async with self.session.get("https://meme-api.com/gimme") as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        if not data.get("nsfw", True):  # Only show SFW memes
                            embed = self.create_embed(
                                title=f"😂 {data.get('title', 'Random Meme')}",
                                color=hikari.Color(0xFF6B35),
                            )

                            embed.set_image(data.get("url"))
                            embed.add_field("Subreddit", f"r/{data.get('subreddit', 'unknown')}", inline=True)
                            embed.add_field("Upvotes", f"👍 {data.get('ups', 0)}", inline=True)

                            if data.get("postLink"):
                                embed.add_field("Source", f"[View on Reddit]({data['postLink']})", inline=False)

                            await ctx.respond(embed=embed)
                            await self.log_command_usage(ctx, "meme", True)
                            return
                        else:
                            # Try again with a different API endpoint
                            raise Exception("NSFW meme, trying different source")

            except Exception:
                # Fallback to a different meme API
                try:
                    async with self.session.get("https://api.imgflip.com/get_memes") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("success") and data.get("data", {}).get("memes"):
                                meme = random.choice(data["data"]["memes"])

                                embed = self.create_embed(
                                    title=f"😂 {meme.get('name', 'Random Meme')}",
                                    color=hikari.Color(0xFF6B35),
                                )

                                embed.set_image(meme.get("url"))
                                embed.set_footer("Powered by Imgflip")

                                await ctx.respond(embed=embed)
                                await self.log_command_usage(ctx, "meme", True)
                                return
                except Exception:
                    pass

            # Final fallback
            embed = self.create_embed(
                title="😅 Meme Service Unavailable",
                description="Sorry, couldn't fetch a meme right now. The meme gods are taking a break!",
                color=hikari.Color(0xFFAA00),
            )
            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "meme", True)

        except Exception as e:
            logger.error(f"Error in meme command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to get a meme. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "meme", False, str(e))

    @command(
        name="fact",
        description="Get a random interesting fact",
        aliases=["randomfact"],
    )
    async def random_fact(self, ctx: lightbulb.Context) -> None:
        try:
            fact_text = None

            # Try online API first
            if self.session:
                try:
                    async with self.session.get("https://uselessfacts.jsph.pl/random.json?language=en") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            fact_text = data.get("text")
                except Exception:
                    pass

            # Fallback to local facts
            if not fact_text:
                local_facts = [
                    "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible.",
                    "A single cloud can weigh more than a million pounds. Despite floating in the sky, clouds are made of water droplets that collectively have significant mass.",
                    "Bananas are berries, but strawberries aren't. Botanically speaking, berries must have seeds inside their flesh.",
                    "The shortest war in history lasted only 38-45 minutes. It was between Britain and Zanzibar in 1896.",
                    "Octopuses have three hearts and blue blood. Two hearts pump blood to the gills, while the third pumps to the rest of the body.",
                    "A group of flamingos is called a 'flamboyance.' Other collective nouns include a 'murder' of crows and a 'wisdom' of wombats.",
                    "The human brain contains approximately 86 billion neurons, roughly the same number of stars in the Milky Way galaxy.",
                    "Butterflies taste with their feet. They have chemoreceptors on their feet that help them identify suitable plants for laying eggs.",
                    "The Great Wall of China isn't visible from space with the naked eye, contrary to popular belief.",
                    "A day on Venus is longer than its year. Venus rotates so slowly that it takes longer to complete one rotation than to orbit the Sun.",
                    "Sharks have been around longer than trees. Sharks appeared about 400 million years ago, while trees appeared around 350 million years ago.",
                    "The dot over a lowercase 'i' or 'j' is called a tittle.",
                    "Wombat poop is cube-shaped. This helps prevent it from rolling away and marks their territory more effectively.",
                    "There are more possible games of chess than atoms in the observable universe.",
                    "Sea otters hold hands while sleeping to prevent themselves from drifting apart."
                ]
                fact_text = random.choice(local_facts)

            embed = self.create_embed(
                title="🤓 Random Fact",
                description=fact_text,
                color=hikari.Color(0x4169E1),
            )

            # Add a random educational emoji
            educational_emojis = ["🧠", "📚", "🔬", "🌟", "💡", "🎓", "🧪", "🔍"]
            emoji = random.choice(educational_emojis)
            embed.set_footer(f"{emoji} The more you know!")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "fact", True)

        except Exception as e:
            logger.error(f"Error in fact command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to get a fact. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "fact", False, str(e))

    @command(
        name="would-you-rather",
        description="Get a would you rather question",
        aliases=["wyr", "wouldyourather"],
        permission_node="fun.games",
    )
    async def would_you_rather(self, ctx: lightbulb.Context) -> None:
        try:
            # Local would you rather questions
            wyr_questions = [
                ("Have the ability to fly", "Have the ability to become invisible"),
                ("Always have to sing rather than speak", "Always have to dance rather than walk"),
                ("Live in a world without music", "Live in a world without movies"),
                ("Be able to read minds", "Be able to see the future"),
                ("Have unlimited money", "Have unlimited time"),
                ("Only be able to whisper", "Only be able to shout"),
                ("Fight 100 duck-sized horses", "Fight 1 horse-sized duck"),
                ("Have taste buds in your fingers", "Have your tongue always taste like your least favorite food"),
                ("Be famous but poor", "Be unknown but rich"),
                ("Live underwater", "Live in space"),
                ("Have no arms", "Have no legs"),
                ("Be able to control fire", "Be able to control water"),
                ("Never use the internet again", "Never watch TV/movies again"),
                ("Have perfect memory", "Have perfect intuition"),
                ("Be stuck in traffic for 2 hours every day", "Always have slow internet"),
                ("Have hiccups for the rest of your life", "Feel like you need to sneeze but can't for the rest of your life"),
                ("Only be able to eat sweet foods", "Only be able to eat savory foods"),
                ("Be 3 feet tall", "Be 8 feet tall"),
                ("Have everything you eat taste like your favorite food", "Have everything you eat be your favorite food but taste terrible"),
                ("Live in a world where everything is purple", "Live in a world where everything is silent")
            ]

            option_a, option_b = random.choice(wyr_questions)

            embed = self.create_embed(
                title="🤔 Would You Rather...",
                color=hikari.Color(0xFF1493),
            )

            embed.add_field(
                "🅰️ Option A",
                option_a,
                inline=True
            )

            embed.add_field(
                "🅱️ Option B",
                option_b,
                inline=True
            )

            embed.set_footer("Click the buttons to vote! Results update live.")

            # Create view with voting buttons
            view = WouldYouRatherView(option_a, option_b)

            # Send message with view
            miru_client = getattr(self.bot, "miru_client", None)
            if miru_client:
                await ctx.respond(embed=embed, components=view)
                miru_client.start_view(view)
            else:
                await ctx.respond(embed=embed)

            await self.log_command_usage(ctx, "would-you-rather", True)

        except Exception as e:
            logger.error(f"Error in would-you-rather command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to get a would you rather question. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "would-you-rather", False, str(e))

    # Web Panel Implementation
    def get_panel_info(self) -> Dict[str, Any]:
        """Return metadata about this plugin's web panel"""
        return {
            "name": "Fun & Games",
            "description": "Interactive fun commands and games panel",
            "route": "/plugin/fun",
            "icon": "🎮",
            "nav_order": 10
        }

    def register_web_routes(self, app: FastAPI) -> None:
        """Register web routes for the fun plugin"""

        @app.get("/plugin/fun", response_class=HTMLResponse)
        async def fun_panel(request: Request):
            """Main fun plugin panel"""
            return self.render_plugin_template(request, "panel.html")

        @app.post("/plugin/fun/api/roll")
        async def api_roll_dice(request: Request):
            """API endpoint for dice rolling"""
            import random
            try:
                form_data = await request.form()
                dice = form_data.get("dice", "1d6")

                if "d" not in dice.lower():
                    return HTMLResponse("❌ <strong>Invalid Format</strong><br>Please use dice notation like 1d6, 2d20, etc.")

                parts = dice.lower().split("d")
                if len(parts) != 2:
                    return HTMLResponse("❌ <strong>Invalid Format</strong><br>Please use dice notation like 1d6, 2d20, etc.")

                num_dice = int(parts[0]) if parts[0] else 1
                num_sides = int(parts[1])

                if not (1 <= num_dice <= 20) or not (2 <= num_sides <= 1000):
                    return HTMLResponse("❌ <strong>Invalid Range</strong><br>Dice: 1-20, Sides: 2-1000")

                rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
                total = sum(rolls)

                if num_dice == 1:
                    result = f"🎲 <strong>You rolled a {total}!</strong>"
                else:
                    rolls_text = ", ".join(str(roll) for roll in rolls)
                    result = f"🎲 <strong>Rolls:</strong> {rolls_text}<br><strong>Total:</strong> {total}"

                return HTMLResponse(result)

            except Exception as e:
                return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

        @app.post("/plugin/fun/api/coinflip")
        async def api_coinflip(request: Request):
            """API endpoint for coin flipping"""
            import random
            try:
                result = random.choice(["Heads", "Tails"])
                return HTMLResponse(f"🪙 <strong>The coin landed on {result}!</strong>")
            except Exception as e:
                return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

        @app.post("/plugin/fun/api/8ball")
        async def api_8ball(request: Request):
            """API endpoint for magic 8-ball"""
            import random
            try:
                form_data = await request.form()
                question = form_data.get("question", "").strip()

                if not question:
                    return HTMLResponse("❌ <strong>Please ask a question!</strong>")

                responses = [
                    "It is certain", "It is decidedly so", "Without a doubt", "Yes definitely",
                    "You may rely on it", "As I see it, yes", "Most likely", "Outlook good",
                    "Yes", "Signs point to yes", "Reply hazy, try again", "Ask again later",
                    "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
                    "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"
                ]

                response = random.choice(responses)
                return HTMLResponse(f"🎱 <strong>Question:</strong> {question}<br><strong>Answer:</strong> {response}")

            except Exception as e:
                return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

        @app.post("/plugin/fun/api/random")
        async def api_random_number(request: Request):
            """API endpoint for random number generation"""
            import random
            try:
                form_data = await request.form()
                min_val = int(form_data.get("min", 1))
                max_val = int(form_data.get("max", 100))

                if min_val > max_val:
                    return HTMLResponse("❌ <strong>Invalid Range</strong><br>Minimum cannot be greater than maximum")

                if abs(max_val - min_val) > 10_000_000:
                    return HTMLResponse("❌ <strong>Range Too Large</strong><br>Range cannot exceed 10 million numbers")

                result = random.randint(min_val, max_val)
                total_possibilities = max_val - min_val + 1

                return HTMLResponse(f"🎯 <strong>Generated:</strong> {result}<br><strong>Range:</strong> {min_val} - {max_val}<br><strong>Possibilities:</strong> {total_possibilities:,}")

            except Exception as e:
                return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

        @app.post("/plugin/fun/api/joke")
        async def api_joke(request: Request):
            """API endpoint for random jokes"""
            import random
            try:
                # Try online API first, fallback to local jokes
                if self.session:
                    try:
                        async with self.session.get("https://v2.jokeapi.dev/joke/Programming,Miscellaneous?blacklistFlags=nsfw,religious,political,racist,sexist,explicit") as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data["type"] == "single":
                                    joke_text = data["joke"]
                                else:
                                    joke_text = f"{data['setup']}<br><br>{data['delivery']}"
                                return HTMLResponse(f"😂 <strong>Here's a joke for you:</strong><br><br>{joke_text}")
                    except:
                        pass

                # Fallback to local jokes
                local_jokes = [
                    "Why don't scientists trust atoms? Because they make up everything!",
                    "Why did the scarecrow win an award? He was outstanding in his field!",
                    "Why don't eggs tell jokes? They'd crack each other up!",
                    "What do you call a fake noodle? An impasta!",
                    "Why did the math book look so sad? Because it was full of problems!",
                ]

                joke = random.choice(local_jokes)
                return HTMLResponse(f"😂 <strong>Here's a joke for you:</strong><br><br>{joke}")

            except Exception as e:
                return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")

        @app.post("/plugin/fun/api/quote")
        async def api_quote(request: Request):
            """API endpoint for inspirational quotes"""
            import random
            try:
                # Try online API first
                if self.session:
                    try:
                        async with self.session.get("https://api.quotable.io/random?maxLength=150") as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                quote_text = data.get("content")
                                quote_author = data.get("author")
                                if quote_text and quote_author:
                                    return HTMLResponse(f'💭 <strong>Inspirational Quote:</strong><br><br><em>"{quote_text}"</em><br><br>— {quote_author}')
                    except:
                        pass

                # Fallback to local quotes
                local_quotes = [
                    ("The only way to do great work is to love what you do.", "Steve Jobs"),
                    ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
                    ("Life is what happens to you while you're busy making other plans.", "John Lennon"),
                    ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
                    ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
                    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
                ]

                quote_text, quote_author = random.choice(local_quotes)
                return HTMLResponse(f'💭 <strong>Inspirational Quote:</strong><br><br><em>"{quote_text}"</em><br><br>— {quote_author}')

            except Exception as e:
                return HTMLResponse(f"❌ <strong>Error:</strong> {str(e)}")
