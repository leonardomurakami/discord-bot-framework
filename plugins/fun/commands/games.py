from __future__ import annotations

import html
import logging
import random
from typing import TYPE_CHECKING, Any, Callable

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import (
    API_ENDPOINTS,
    DEFAULT_TRIVIA_QUESTIONS,
    DEFAULT_WYR_QUESTIONS,
    DICE_LIMITS,
    RANDOM_NUMBER_LIMIT,
)
from ..views import TriviaView, WouldYouRatherView

if TYPE_CHECKING:
    from ..fun_plugin import FunPlugin

logger = logging.getLogger(__name__)


def setup_game_commands(plugin: "FunPlugin") -> list[Callable[..., Any]]:
    """Register interactive game-style commands."""

    @command(
        name="roll",
        description="Roll dice (format: NdN, e.g., 2d6)",
        aliases=["r"],
        permission_node="basic.games",
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
    async def roll_dice(ctx: lightbulb.Context, dice: str = "1d6") -> None:
        try:
            if "d" not in dice.lower():
                embed = plugin.create_embed(
                    title="❌ Invalid Format",
                    description="Please use dice notation like `1d6`, `2d20`, etc.",
                    color=hikari.Color(0xFF0000),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            parts = dice.lower().split("d")
            if len(parts) != 2:
                raise ValueError("Invalid dice format")

            num_dice = int(parts[0]) if parts[0] else 1
            num_sides = int(parts[1])

            if num_dice < DICE_LIMITS["min_dice"] or num_dice > DICE_LIMITS["max_dice"]:
                embed = plugin.create_embed(
                    title="❌ Invalid Range",
                    description="Number of dice must be between 1 and 20.",
                    color=hikari.Color(0xFF0000),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if num_sides < DICE_LIMITS["min_sides"] or num_sides > DICE_LIMITS["max_sides"]:
                embed = plugin.create_embed(
                    title="❌ Invalid Range",
                    description="Number of sides must be between 2 and 1000.",
                    color=hikari.Color(0xFF0000),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
            total = sum(rolls)

            if num_dice == 1:
                result_text = f"🎲 You rolled a **{total}**!"
            else:
                rolls_text = ", ".join(str(roll) for roll in rolls)
                result_text = f"🎲 You rolled: {rolls_text}\nTotal: **{total}**"

            embed = plugin.create_embed(
                title=f"Dice Roll ({dice})",
                description=result_text,
                color=hikari.Color(0x00FF00),
            )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "roll", True)

        except ValueError:
            embed = plugin.create_embed(
                title="❌ Invalid Format",
                description="Please use valid dice notation like `1d6`, `2d20`, etc.",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "roll", False, "Invalid format")

        except Exception as exc:
            logger.error("Error in roll command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"An error occurred: {exc}",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "roll", False, str(exc))

    @command(name="coinflip", description="Flip a coin", permission_node="basic.games")
    async def flip_coin(ctx: lightbulb.Context) -> None:
        try:
            result = random.choice(["Heads", "Tails"])
            emoji = "🪙"

            embed = plugin.create_embed(
                title="Coin Flip",
                description=f"{emoji} The coin landed on **{result}**!",
                color=hikari.Color(0xFFD700),
            )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "coinflip", True)

        except Exception as exc:
            logger.error("Error in coinflip command: %s", exc)
            await plugin.log_command_usage(ctx, "coinflip", False, str(exc))

    @command(
        name="8ball",
        description="Ask the magic 8-ball a question",
        permission_node="basic.games",
        arguments=[CommandArgument("question", hikari.OptionType.STRING, "Your question for the 8-ball")],
    )
    async def magic_8ball(ctx: lightbulb.Context, question: str) -> None:
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

            embed = plugin.create_embed(
                title="🎱 Magic 8-Ball",
                description=f"**Question:** {question}\n**Answer:** {response}",
                color=hikari.Color(0x8B00FF),
            )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "8ball", True)

        except Exception as exc:
            logger.error("Error in 8ball command: %s", exc)
            await plugin.log_command_usage(ctx, "8ball", False, str(exc))

    @command(
        name="choose",
        description="Let the bot choose between options",
        arguments=[
            CommandArgument("option1", hikari.OptionType.STRING, "Option 1"),
            CommandArgument("option2", hikari.OptionType.STRING, "Option 2"),
        ],
    )
    async def choose_option(ctx: lightbulb.Context, option1: str, option2: str) -> None:
        try:
            choices = [option1, option2]

            if len(choices) < 2:
                embed = plugin.create_embed(
                    title="❌ Not Enough Options",
                    description="Please provide at least 2 options.",
                    color=hikari.Color(0xFF0000),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            chosen = random.choice(choices)

            embed = plugin.create_embed(
                title="🤔 Choice Made",
                description=f"I choose: **{chosen}**",
                color=hikari.Color(0x00FF00),
            )

            options_text = "\n".join(f"• {choice}" for choice in choices)
            embed.add_field("Options", options_text, inline=False)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "choose", True)

        except Exception as exc:
            logger.error("Error in choose command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"An error occurred: {exc}",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "choose", False, str(exc))

    @command(
        name="random",
        description="Generate random numbers within a range",
        aliases=["rng", "rand"],
        permission_node="basic.games",
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
    async def random_number(ctx: lightbulb.Context, min_value: int = 1, max_value: int = 100) -> None:
        try:
            if min_value > max_value:
                embed = plugin.create_embed(
                    title="❌ Invalid Range",
                    description="Minimum value cannot be greater than maximum value.",
                    color=hikari.Color(0xFF0000),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if abs(max_value - min_value) > RANDOM_NUMBER_LIMIT:
                embed = plugin.create_embed(
                    title="❌ Range Too Large",
                    description=f"Range cannot exceed {RANDOM_NUMBER_LIMIT:,} numbers.",
                    color=hikari.Color(0xFF0000),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            result = random.randint(min_value, max_value)

            embed = plugin.create_embed(
                title="🎲 Random Number",
                description=f"🎯 Generated: **{result}**",
                color=hikari.Color(0x9932CC),
            )

            embed.add_field("Range", f"{min_value} - {max_value}", inline=True)
            embed.add_field("Total Possibilities", str(max_value - min_value + 1), inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "random", True)

        except Exception as exc:
            logger.error("Error in random command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"An error occurred: {exc}",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "random", False, str(exc))

    @command(
        name="trivia",
        description="Start an interactive trivia question",
        permission_node="basic.games",
    )
    async def trivia_question(ctx: lightbulb.Context) -> None:
        try:
            question_data: dict[str, Any] | None = None
            if plugin.session:
                try:
                    async with plugin.session.get(API_ENDPOINTS["trivia"]) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data["response_code"] == 0 and data["results"]:
                                question_data = data["results"][0]
                except Exception:
                    pass

            if not question_data:
                question_data = random.choice(DEFAULT_TRIVIA_QUESTIONS)

            question_text = html.unescape(question_data["question"])

            embed = plugin.create_embed(
                title="🧠 Trivia Time!",
                description=f"**Category:** {question_data.get('category', 'General')}\n\n**Question:**\n{question_text}",
                color=hikari.Color(0x9932CC),
            )

            embed.set_footer("⏱️ 30s remaining • Click the correct answer!")

            view = TriviaView(question_data, embed)

            miru_client = getattr(plugin.bot, "miru_client", None)
            if miru_client:
                message = await ctx.respond(embed=embed, components=view)
                miru_client.start_view(view)

                if message is None:
                    logger.debug("ctx.respond() returned None - miru will set view.message later")
                elif hasattr(message, "message"):
                    view.trivia_message = message.message
                    view.message = message.message
                    logger.debug("Set trivia_message from message.message: %s", type(message.message))
                elif hasattr(message, "id"):
                    view.trivia_message = message
                    view.message = message
                    logger.debug("Set trivia_message from message: %s", type(message))
                else:
                    logger.warning("Message object has no 'message' or 'id' attribute. Type: %s", type(message))

                if view.trivia_message:
                    view.start_countdown(view.trivia_message)
                else:
                    logger.debug("No immediate message reference - countdown will start when miru sets view.message")
            else:
                await ctx.respond(embed=embed)

            await plugin.log_command_usage(ctx, "trivia", True)

        except Exception as exc:
            logger.error("Error in trivia command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to start trivia question. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "trivia", False, str(exc))

    @command(
        name="would-you-rather",
        description="Get a would you rather question",
        aliases=["wyr", "wouldyourather"],
        permission_node="basic.games",
    )
    async def would_you_rather(ctx: lightbulb.Context) -> None:
        try:
            option_a, option_b = random.choice(DEFAULT_WYR_QUESTIONS)

            embed = plugin.create_embed(
                title="🤔 Would You Rather...",
                color=hikari.Color(0xFF1493),
            )

            embed.add_field("🅰️ Option A", option_a, inline=True)
            embed.add_field("🅱️ Option B", option_b, inline=True)
            embed.set_footer("Click the buttons to vote! Results update live.")

            view = WouldYouRatherView(option_a, option_b)

            miru_client = getattr(plugin.bot, "miru_client", None)
            if miru_client:
                await ctx.respond(embed=embed, components=view)
                miru_client.start_view(view)
            else:
                await ctx.respond(embed=embed)

            await plugin.log_command_usage(ctx, "would-you-rather", True)

        except Exception as exc:
            logger.error("Error in would-you-rather command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to get a would you rather question. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "would-you-rather", False, str(exc))

    return [
        roll_dice,
        flip_coin,
        magic_8ball,
        choose_option,
        random_number,
        trivia_question,
        would_you_rather,
    ]
