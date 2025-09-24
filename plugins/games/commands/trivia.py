from __future__ import annotations

import html
import logging
import random
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import (
    DEFAULT_TRIVIA_QUESTIONS,
    DIFFICULTY_EMOJIS,
    EMBED_COLORS,
    TRIVIA_CATEGORIES,
    TRIVIA_DIFFICULTIES,
    games_settings,
)
from ..views import TriviaView

if TYPE_CHECKING:
    from ..plugin import GamesPlugin

logger = logging.getLogger(__name__)


def setup_trivia_commands(plugin: GamesPlugin) -> list[Callable[..., Any]]:
    """Register trivia commands."""

    @command(
        name="trivia",
        description="Start an interactive trivia question with difficulty and category options",
        permission_node="basic.games.trivia.play",
        arguments=[
            CommandArgument(
                "difficulty",
                hikari.OptionType.STRING,
                "Question difficulty",
                required=False,
                choices=[
                    hikari.CommandChoice(name="Easy 🟢", value="easy"),
                    hikari.CommandChoice(name="Medium 🟡", value="medium"),
                    hikari.CommandChoice(name="Hard 🔴", value="hard"),
                ],
            ),
            CommandArgument(
                "category",
                hikari.OptionType.STRING,
                "Question category",
                required=False,
                choices=[
                    hikari.CommandChoice(name=name.title(), value=name)
                    for name in sorted(TRIVIA_CATEGORIES.keys())
                ][:25],  # Discord limit
            ),
        ],
    )
    async def trivia_question(
        ctx: lightbulb.Context, difficulty: str | None = None, category: str | None = None
    ) -> None:
        try:
            # Check if we're in a guild (trivia doesn't work in DMs)
            if not ctx.guild_id:
                embed = plugin.create_embed(
                    title="❌ Error",
                    description="Trivia can only be played in servers, not in DMs!",
                    color=hikari.Color(EMBED_COLORS["error"]),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            question_data: dict[str, Any] | None = None

            # Try to get question from API first
            if plugin.session:
                try:
                    # Build API URL with parameters
                    api_url = games_settings.trivia_api_url
                    params = []

                    if difficulty and difficulty in TRIVIA_DIFFICULTIES:
                        params.append(f"difficulty={difficulty}")

                    if category and category in TRIVIA_CATEGORIES:
                        params.append(f"category={TRIVIA_CATEGORIES[category]}")

                    if params:
                        api_url += "&" + "&".join(params)

                    async with plugin.session.get(api_url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data["response_code"] == 0 and data["results"]:
                                question_data = data["results"][0]
                except Exception as exc:
                    logger.debug("API request failed: %s", exc)

            # Fallback to custom questions or defaults
            if not question_data:
                # Try custom questions for this guild first
                custom_questions = await plugin.get_custom_questions(ctx.guild_id, category, difficulty)
                if custom_questions:
                    question_data = random.choice(custom_questions).to_dict()
                else:
                    # Use default questions
                    available_questions = DEFAULT_TRIVIA_QUESTIONS
                    if difficulty:
                        available_questions = [q for q in available_questions if q.get("difficulty") == difficulty]
                    if category:
                        available_questions = [q for q in available_questions if q.get("category", "").lower() == category.lower()]

                    if available_questions:
                        question_data = random.choice(available_questions)
                    else:
                        question_data = random.choice(DEFAULT_TRIVIA_QUESTIONS)

            if not question_data:
                embed = plugin.create_embed(
                    title="❌ Error",
                    description="Failed to get a trivia question. Please try again!",
                    color=hikari.Color(EMBED_COLORS["error"]),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            question_text = html.unescape(question_data["question"])
            question_category = question_data.get("category", "General")
            question_difficulty = question_data.get("difficulty", "medium")

            # Check if this should be a time attack question (10% chance)
            is_time_attack = random.random() < 0.1

            difficulty_emoji = DIFFICULTY_EMOJIS.get(question_difficulty, "⚪")
            title = "🧠 Trivia Time!"
            if is_time_attack:
                title = "⚡ Time Attack Trivia!"

            # Create description with Discord timestamp countdown
            import time as time_module
            end_time = int(time_module.time()) + games_settings.trivia_timeout_seconds

            base_description = (f"**Category:** {question_category}\n"
                               f"**Difficulty:** {difficulty_emoji} {question_difficulty.title()}\n\n"
                               f"**Question:**\n{question_text}")

            initial_timer = f"\n\n⏱️ **Ends <t:{end_time}:R>** • Click the correct answer!"
            if is_time_attack:
                initial_timer += "\n⚡ **Time Attack: Extra points for speed!**"

            embed = plugin.create_embed(
                title=title,
                description=base_description + initial_timer,
                color=hikari.Color(EMBED_COLORS["trivia"]),
            )

            view = TriviaView(question_data, embed, plugin, ctx.guild_id, ctx.author.id, is_time_attack)

            miru_client = getattr(plugin.bot, "miru_client", None)
            if miru_client:
                # Set start time before sending
                view.start_time = time.time()

                # Send the message and get the snowflake
                response_snowflake = await ctx.respond(embed=embed, components=view)

                # Bind the view to the message using the snowflake
                miru_client.start_view(view, bind_to=response_snowflake)

                # Start the countdown timer
                view.start_countdown()
            else:
                await ctx.respond(embed=embed)

            await plugin.log_command_usage(ctx, "trivia", True)

        except Exception as exc:
            logger.error("Error in trivia command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to start trivia question. Try again later!",
                color=hikari.Color(EMBED_COLORS["error"]),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "trivia", False, str(exc))

    @command(
        name="trivia-stats",
        description="View your trivia statistics",
        permission_node="basic.games.trivia.play",
        arguments=[
            CommandArgument(
                "user",
                hikari.OptionType.USER,
                "User to view stats for",
                required=False,
            ),
        ],
    )
    async def trivia_stats(ctx: lightbulb.Context, user: hikari.User | None = None) -> None:
        target_user = user or ctx.author

        try:
            stats = await plugin.get_trivia_stats(target_user.id, ctx.guild_id)

            if not stats or stats.total_questions == 0:
                embed = plugin.create_embed(
                    title="📊 Trivia Statistics",
                    description=f"{target_user.mention} hasn't played trivia yet!",
                    color=hikari.Color(EMBED_COLORS["info"]),
                )
            else:
                embed = plugin.create_embed(
                    title=f"📊 Trivia Statistics - {target_user.username}",
                    color=hikari.Color(EMBED_COLORS["trivia"]),
                )

                embed.add_field(
                    "📈 Overall Performance",
                    f"**Questions Answered:** {stats.total_questions:,}\n"
                    f"**Correct Answers:** {stats.correct_answers:,}\n"
                    f"**Accuracy:** {stats.accuracy:.1f}%\n"
                    f"**Total Points:** {stats.total_points:,}",
                    inline=True,
                )

                embed.add_field(
                    "🎯 By Difficulty",
                    f"🟢 Easy: {stats.easy_correct:,}\n"
                    f"🟡 Medium: {stats.medium_correct:,}\n"
                    f"🔴 Hard: {stats.hard_correct:,}",
                    inline=True,
                )

                embed.add_field(
                    "🔥 Streaks & Speed",
                    f"**Current Streak:** {stats.current_streak}\n"
                    f"**Best Streak:** {stats.best_streak}\n"
                    f"**Fast Answers:** {stats.fast_answers}\n"
                    f"**Hints Used:** {stats.hints_used}",
                    inline=True,
                )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "trivia-stats", True)

        except Exception as exc:
            logger.error("Error in trivia-stats command: %s", exc)
            await plugin.log_command_usage(ctx, "trivia-stats", False, str(exc))

    @command(
        name="trivia-leaderboard",
        description="View the trivia leaderboard for this server",
        permission_node="basic.games.trivia.play",
        arguments=[
            CommandArgument(
                "leaderboard_type",
                hikari.OptionType.STRING,
                "Leaderboard type",
                required=False,
                choices=[
                    hikari.CommandChoice(name="Points", value="points"),
                    hikari.CommandChoice(name="Accuracy", value="accuracy"),
                    hikari.CommandChoice(name="Best Streak", value="streak"),
                ],
                default="points",
            ),
        ],
    )
    async def trivia_leaderboard(ctx: lightbulb.Context, leaderboard_type: str = "points") -> None:
        try:
            leaderboard_data = await plugin.get_leaderboard(ctx.guild_id, leaderboard_type)

            if not leaderboard_data:
                embed = plugin.create_embed(
                    title="🏆 Trivia Leaderboard",
                    description="No trivia data available yet! Start playing to see rankings.",
                    color=hikari.Color(EMBED_COLORS["info"]),
                )
            else:
                type_emoji = {"points": "💎", "accuracy": "🎯", "streak": "🔥"}.get(leaderboard_type, "🏆")
                embed = plugin.create_embed(
                    title=f"{type_emoji} Trivia Leaderboard - {leaderboard_type.title()}",
                    color=hikari.Color(EMBED_COLORS["trivia"]),
                )

                leaderboard_text = ""
                for i, entry in enumerate(leaderboard_data[:10], 1):
                    medal = ""
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"

                    user_mention = f"<@{entry['user_id']}>"
                    value = entry[leaderboard_type]

                    if leaderboard_type == "accuracy":
                        value_str = f"{value:.1f}%"
                    else:
                        value_str = f"{value:,}"

                    leaderboard_text += f"{medal} **#{i}** {user_mention} - {value_str}\n"

                embed.description = leaderboard_text or "No data available"

                embed.set_footer("Showing top 10 players • Use /trivia-stats to see your detailed stats")

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "trivia-leaderboard", True)

        except Exception as exc:
            logger.error("Error in trivia-leaderboard command: %s", exc)
            await plugin.log_command_usage(ctx, "trivia-leaderboard", False, str(exc))

    return [trivia_question, trivia_stats, trivia_leaderboard]
