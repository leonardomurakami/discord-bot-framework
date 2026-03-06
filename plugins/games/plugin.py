from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import aiohttp
import hikari

from bot.plugins.base import BasePlugin
from bot.plugins.mixins import DatabaseMixin

from .commands.trivia import setup_trivia_commands
from .config import ANGLE_MAX_ATTEMPTS, ANGLE_POINTS, EMBED_COLORS, games_settings

if TYPE_CHECKING:
    from bot.core.bot import DiscordBot

logger = logging.getLogger(__name__)


class GamesPlugin(DatabaseMixin, BasePlugin):
    """Interactive games plugin with trivia, angle game, RPS, scoring, and achievements."""

    def __init__(self, bot: DiscordBot) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession | None = None

        # Register database models
        from .models import CustomQuestion, GuildLeaderboard, TriviaAchievement, TriviaStats
        from .models.angle import AngleGame, AngleStats
        self.register_models(TriviaStats, TriviaAchievement, CustomQuestion, GuildLeaderboard, AngleGame, AngleStats)

        # Register commands
        self._register_commands()

    async def on_load(self) -> None:
        """Initialize the plugin and start HTTP session."""
        await super().on_load()

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
        from .commands.angle import setup_angle_commands
        from .commands.rps import setup_rps_commands

        trivia_commands = setup_trivia_commands(self)
        angle_commands = setup_angle_commands(self)
        rps_commands = setup_rps_commands(self)

        for command_func in (*trivia_commands, *angle_commands, *rps_commands):
            setattr(self, command_func.__name__, command_func)

    # -------------------------------------------------------------------------
    # Trivia helpers
    # -------------------------------------------------------------------------

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

    async def get_trivia_achievements(self, user_id: int, guild_id: int):
        """Get all unlocked achievements for a user in a guild."""
        from .models import TriviaAchievement

        async with self.db_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TriviaAchievement).where(
                    TriviaAchievement.user_id == user_id,
                    TriviaAchievement.guild_id == guild_id,
                ).order_by(TriviaAchievement.unlocked_at)
            )
            return result.scalars().all()

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
                    TriviaStats.total_questions >= 5
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

            return [
                {
                    "user_id": s.user_id,
                    "points": s.total_points,
                    "accuracy": s.accuracy,
                    "streak": s.best_streak,
                }
                for s in stats_list
            ]

    async def award_points(
        self,
        user_id: int,
        guild_id: int,
        points: int,
        difficulty: str,
        used_hint: bool,
        response_time: float,
        is_correct: bool = True,
        channel_id: int | None = None,
    ) -> None:
        """Award points to a user and update their trivia statistics."""
        from .models import TriviaStats

        async with self.db_session() as session:
            from sqlalchemy import select

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

            stats.total_questions += 1

            stats.record_result(is_correct)

            if is_correct:
                stats.correct_answers += 1
                stats.total_points += points
                stats.current_streak += 1

                if difficulty == "easy":
                    stats.easy_correct += 1
                elif difficulty == "medium":
                    stats.medium_correct += 1
                elif difficulty == "hard":
                    stats.hard_correct += 1

                # Apply streak bonus (bug fix: was never applied before)
                streak_bonus = min(
                    stats.current_streak * games_settings.trivia_streak_bonus,
                    games_settings.trivia_max_streak_bonus,
                )
                stats.total_points += streak_bonus
            else:
                stats.current_streak = 0

            if stats.current_streak > stats.best_streak:
                stats.best_streak = stats.current_streak

            if is_correct and response_time <= 5.0:
                stats.fast_answers += 1

            if used_hint:
                stats.hints_used += 1

            await session.commit()

            await self._check_achievements(user_id, guild_id, stats, session, channel_id=channel_id)

    async def _check_achievements(
        self, user_id: int, guild_id: int, stats: Any, session: Any, channel_id: int | None = None
    ) -> None:
        """Check and award any new achievements, notifying the channel if possible."""
        from sqlalchemy import select

        from .config import TRIVIA_ACHIEVEMENTS
        from .models import TriviaAchievement

        result = await session.execute(
            select(TriviaAchievement).where(
                TriviaAchievement.user_id == user_id,
                TriviaAchievement.guild_id == guild_id
            )
        )
        existing_achievements = {ach.achievement_id for ach in result.scalars().all()}

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
            elif req_type == "perfect_accuracy" and stats.recent_perfect:
                earned = True

            if earned:
                achievement = TriviaAchievement(
                    user_id=user_id,
                    guild_id=guild_id,
                    achievement_id=achievement_id,
                    name=achievement_data["name"],
                    description=achievement_data["description"],
                    emoji=achievement_data["emoji"],
                )
                session.add(achievement)
                await session.commit()
                logger.info("Awarded achievement '%s' to user %s in guild %s", achievement_id, user_id, guild_id)

                # Notify channel
                if channel_id:
                    try:
                        embed = hikari.Embed(
                            title=f"{achievement_data['emoji']} Achievement Unlocked!",
                            description=(
                                f"<@{user_id}> earned **{achievement_data['name']}**\n"
                                f"{achievement_data['description']}"
                            ),
                            color=hikari.Color(EMBED_COLORS["achievement"]),
                        )
                        await self.bot.rest.create_message(channel_id, embed=embed)
                    except Exception as exc:
                        logger.warning("Failed to send achievement notification: %s", exc)

    # -------------------------------------------------------------------------
    # Angle game helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def get_daily_angle(user_id: int) -> int:
        """Return a deterministic daily angle (1-360) unique per user per UTC day."""
        today = datetime.now(UTC).date().isoformat()
        seed = f"{today}:{user_id}"
        hash_bytes = hashlib.md5(seed.encode()).digest()  # noqa: S324
        value = int.from_bytes(hash_bytes[:2], "big")
        return (value % 360) + 1  # 1–360

    @staticmethod
    def angle_distance(guess: int, target: int) -> int:
        """Shortest angular distance between guess and target (0–180)."""
        diff = abs(guess - target)
        return min(diff, 360 - diff)

    @staticmethod
    def angle_direction(guess: int, target: int) -> str:
        """Return 'higher' or 'lower' for the shortest clockwise path to target."""
        diff = (target - guess) % 360
        return "higher" if diff <= 180 else "lower"

    async def get_or_create_angle_game(self, user_id: int, guild_id: int) -> dict[str, Any]:
        """Load today's angle game for the user, creating it if it doesn't exist."""
        from .models.angle import AngleGame

        today = datetime.now(UTC).date()
        target = self.get_daily_angle(user_id)

        async with self.db_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(AngleGame).where(
                    AngleGame.user_id == user_id,
                    AngleGame.guild_id == guild_id,
                    AngleGame.game_date == today,
                )
            )
            game = result.scalars().first()

            if not game:
                game = AngleGame(
                    user_id=user_id,
                    guild_id=guild_id,
                    game_date=today,
                    target_angle=target,
                    guesses_json="[]",
                    is_complete=False,
                    won=False,
                    points_awarded=0,
                    points_eligible=True,
                )
                session.add(game)
                await session.commit()
                await session.refresh(game)

            return self._angle_game_to_dict(game)

    async def process_angle_guess(self, user_id: int, guild_id: int, guess: int) -> dict[str, Any]:
        """Record a guess and return the updated game state dict."""
        from .models.angle import AngleGame, AngleStats

        today = datetime.now(UTC).date()

        async with self.db_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(AngleGame).where(
                    AngleGame.user_id == user_id,
                    AngleGame.guild_id == guild_id,
                    AngleGame.game_date == today,
                )
            )
            game = result.scalars().first()

            if not game or game.is_complete:
                return self._angle_game_to_dict(game) if game else {}

            guesses = game.guesses
            guesses.append(guess)
            game.guesses = guesses

            target = game.target_angle
            dist = self.angle_distance(guess, target)
            won = dist == 0
            out_of_attempts = len(guesses) >= ANGLE_MAX_ATTEMPTS

            points = 0
            if game.points_eligible:
                if dist == 0:
                    points = ANGLE_POINTS["exact"]
                elif dist == 1:
                    points = ANGLE_POINTS["close"]
                elif dist == 2:
                    points = ANGLE_POINTS["near"]

            if won or out_of_attempts:
                game.is_complete = True
                game.won = won
                game.points_awarded = points

            await session.commit()

            # Update persistent stats only for point-eligible games that just ended
            if game.is_complete and game.points_eligible:
                stats_result = await session.execute(
                    select(AngleStats).where(
                        AngleStats.user_id == user_id,
                        AngleStats.guild_id == guild_id,
                    )
                )
                stats = stats_result.scalars().first()
                if not stats:
                    stats = AngleStats(user_id=user_id, guild_id=guild_id)
                    session.add(stats)

                stats.total_games += 1
                stats.total_points += points

                if won:
                    stats.wins += 1
                    stats.current_win_streak += 1
                    if stats.current_win_streak > stats.best_win_streak:
                        stats.best_win_streak = stats.current_win_streak
                    if dist == 0 and len(guesses) == 1:
                        stats.exact_wins += 1
                    elif dist <= 2:
                        stats.close_wins += 1
                else:
                    stats.current_win_streak = 0

                await session.commit()

            await session.refresh(game)
            return self._angle_game_to_dict(game)

    @staticmethod
    def _angle_game_to_dict(game: Any) -> dict[str, Any]:
        if game is None:
            return {}
        return {
            "target": game.target_angle,
            "guesses": game.guesses,
            "is_complete": game.is_complete,
            "won": game.won,
            "points_awarded": game.points_awarded,
            "points_eligible": game.points_eligible,
            "attempts_remaining": ANGLE_MAX_ATTEMPTS - len(game.guesses),
        }

    async def get_angle_stats(self, user_id: int, guild_id: int) -> Any:
        """Return AngleStats for a user in a guild, or None."""
        from .models.angle import AngleStats

        async with self.db_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(AngleStats).where(
                    AngleStats.user_id == user_id,
                    AngleStats.guild_id == guild_id,
                )
            )
            return result.scalars().first()
