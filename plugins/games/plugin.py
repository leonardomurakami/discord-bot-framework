from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aiohttp

from bot.plugins.base import BasePlugin
from bot.plugins.mixins import DatabaseMixin

from .commands.trivia import setup_trivia_commands
from .config import games_settings

if TYPE_CHECKING:
    from bot.core.bot import DiscordBot

logger = logging.getLogger(__name__)


class GamesPlugin(DatabaseMixin, BasePlugin):
    """Interactive games plugin with trivia, scoring, and achievements."""

    def __init__(self, bot: DiscordBot) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession | None = None

        # Register database models
        from .models import CustomQuestion, GuildLeaderboard, TriviaAchievement, TriviaStats
        self.register_models(TriviaStats, TriviaAchievement, CustomQuestion, GuildLeaderboard)

        # Register commands
        self._register_commands()

    async def on_load(self) -> None:
        """Initialize the plugin and start HTTP session."""
        await super().on_load()

        # Create HTTP session for API calls
        timeout = aiohttp.ClientTimeout(total=games_settings.api_request_timeout_seconds)
        self.session = aiohttp.ClientSession(timeout=timeout)

        logger.info("Games plugin loaded successfully")

    async def on_unload(self) -> None:
        """Clean up resources and close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

        await super().on_unload()
        logger.info("Games plugin unloaded")

    def _register_commands(self) -> None:
        """Register all game commands."""
        # Register trivia commands
        trivia_commands = setup_trivia_commands(self)
        for command_func in trivia_commands:
            setattr(self, command_func.__name__, command_func)

    async def get_trivia_stats(self, user_id: int, guild_id: int):
        """Get trivia statistics for a user in a guild."""
        from .models import TriviaStats

        async with self.db_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TriviaStats).where(
                    TriviaStats.user_id == user_id,
                    TriviaStats.guild_id == guild_id
                )
            )
            return result.scalars().first()

    async def get_custom_questions(self, guild_id: int, category: str | None = None, difficulty: str | None = None):
        """Get custom questions for a guild with optional filters."""
        from .models import CustomQuestion

        async with self.db_session() as session:
            from sqlalchemy import select
            query = select(CustomQuestion).where(
                CustomQuestion.guild_id == guild_id,
                CustomQuestion.is_active
            )

            if category:
                query = query.where(CustomQuestion.category.ilike(f"%{category}%"))
            if difficulty:
                query = query.where(CustomQuestion.difficulty == difficulty)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_leaderboard(self, guild_id: int, leaderboard_type: str = "points"):
        """Get leaderboard data for a guild."""
        from .models import TriviaStats

        async with self.db_session() as session:
            from sqlalchemy import desc, select

            if leaderboard_type == "points":
                query = select(TriviaStats).where(
                    TriviaStats.guild_id == guild_id,
                    TriviaStats.total_points > 0
                ).order_by(desc(TriviaStats.total_points)).limit(10)
            elif leaderboard_type == "accuracy":
                query = select(TriviaStats).where(
                    TriviaStats.guild_id == guild_id,
                    TriviaStats.total_questions >= 5  # Minimum questions for accuracy ranking
                ).order_by(desc(TriviaStats.correct_answers / TriviaStats.total_questions)).limit(10)
            elif leaderboard_type == "streak":
                query = select(TriviaStats).where(
                    TriviaStats.guild_id == guild_id,
                    TriviaStats.best_streak > 0
                ).order_by(desc(TriviaStats.best_streak)).limit(10)
            else:
                return []

            result = await session.execute(query)
            stats_list = result.scalars().all()

            leaderboard_data = []
            for stats in stats_list:
                entry = {
                    "user_id": stats.user_id,
                    "points": stats.total_points,
                    "accuracy": stats.accuracy,
                    "streak": stats.best_streak,
                }
                leaderboard_data.append(entry)

            return leaderboard_data

    async def award_points(
        self, user_id: int, guild_id: int, points: int, difficulty: str, used_hint: bool, response_time: float, is_correct: bool = True
    ):
        """Award points to a user and update their statistics."""
        from .models import TriviaStats

        async with self.db_session() as session:
            from sqlalchemy import select

            # Get or create user stats
            result = await session.execute(
                select(TriviaStats).where(
                    TriviaStats.user_id == user_id,
                    TriviaStats.guild_id == guild_id
                )
            )
            stats = result.scalars().first()

            if not stats:
                stats = TriviaStats(
                    user_id=user_id,
                    guild_id=guild_id,
                    total_questions=0,
                    correct_answers=0,
                    total_points=0,
                    easy_correct=0,
                    medium_correct=0,
                    hard_correct=0,
                    current_streak=0,
                    best_streak=0,
                    fast_answers=0,
                    hints_used=0,
                )
                session.add(stats)

            # Update stats - always increment total questions
            stats.total_questions += 1

            if is_correct:
                # Correct answer
                stats.correct_answers += 1
                stats.total_points += points
                stats.current_streak += 1

                # Update difficulty stats
                if difficulty == "easy":
                    stats.easy_correct += 1
                elif difficulty == "medium":
                    stats.medium_correct += 1
                elif difficulty == "hard":
                    stats.hard_correct += 1
            else:
                # Wrong answer or no answer - reset streak
                stats.current_streak = 0

            # Update best streak
            if stats.current_streak > stats.best_streak:
                stats.best_streak = stats.current_streak

            # Track fast answers (under 5 seconds) - only for correct answers
            if is_correct and response_time <= 5.0:
                stats.fast_answers += 1

            # Track hints used - for all attempts
            if used_hint:
                stats.hints_used += 1

            await session.commit()

            # Check for new achievements
            await self._check_achievements(user_id, guild_id, stats, session)

    async def _check_achievements(self, user_id: int, guild_id: int, stats, session):
        """Check and award any new achievements."""
        from sqlalchemy import select

        from .config import TRIVIA_ACHIEVEMENTS
        from .models import TriviaAchievement

        # Get existing achievements
        result = await session.execute(
            select(TriviaAchievement).where(
                TriviaAchievement.user_id == user_id,
                TriviaAchievement.guild_id == guild_id
            )
        )
        existing_achievements = {ach.achievement_id for ach in result.scalars().all()}

        # Check each achievement
        for achievement_id, achievement_data in TRIVIA_ACHIEVEMENTS.items():
            if achievement_id in existing_achievements:
                continue

            requirement = achievement_data["requirement"]
            req_type = requirement["type"]
            req_value = requirement["value"]

            earned = False

            if req_type == "correct_answers" and stats.correct_answers >= req_value:
                earned = True
            elif req_type == "streak" and stats.best_streak >= req_value:
                earned = True
            elif req_type == "fast_answers" and stats.fast_answers >= req_value:
                earned = True
            elif req_type == "hard_correct" and stats.hard_correct >= req_value:
                earned = True
            elif req_type == "total_points" and stats.total_points >= req_value:
                earned = True
            # Add more achievement types as needed

            if earned:
                # Award achievement
                achievement = TriviaAchievement(
                    user_id=user_id,
                    guild_id=guild_id,
                    achievement_id=achievement_id,
                    name=achievement_data["name"],
                    description=achievement_data["description"],
                    emoji=achievement_data["emoji"],
                )
                session.add(achievement)
                logger.info(f"Awarded achievement '{achievement_id}' to user {user_id} in guild {guild_id}")
