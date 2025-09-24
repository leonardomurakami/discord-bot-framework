from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models import Base


class TriviaStats(Base):
    """Track individual user trivia statistics."""

    __tablename__ = "trivia_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "guild_id", name="uq_trivia_stats_user_guild"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Basic stats
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    total_points: Mapped[int] = mapped_column(Integer, default=0)

    # Difficulty breakdown
    easy_correct: Mapped[int] = mapped_column(Integer, default=0)
    medium_correct: Mapped[int] = mapped_column(Integer, default=0)
    hard_correct: Mapped[int] = mapped_column(Integer, default=0)

    # Advanced stats
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    fast_answers: Mapped[int] = mapped_column(Integer, default=0)  # Under 5 seconds
    hints_used: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    @property
    def accuracy(self) -> float:
        """Calculate accuracy percentage."""
        if self.total_questions == 0:
            return 0.0
        return (self.correct_answers / self.total_questions) * 100

    def __repr__(self) -> str:
        return f"<TriviaStats(user={self.user_id}, guild={self.guild_id}, correct={self.correct_answers}/{self.total_questions})>"


class TriviaAchievement(Base):
    """Track user achievements in trivia."""

    __tablename__ = "trivia_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "guild_id", "achievement_id", name="uq_trivia_achievement_user_guild_achievement"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    achievement_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Achievement data
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    emoji: Mapped[str] = mapped_column(String(20), nullable=False)

    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    def __repr__(self) -> str:
        return f"<TriviaAchievement(user={self.user_id}, achievement={self.achievement_id})>"


class CustomQuestion(Base):
    """Store custom trivia questions for guilds."""

    __tablename__ = "custom_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Question data
    question: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    incorrect_answer1: Mapped[str] = mapped_column(String(255), nullable=False)
    incorrect_answer2: Mapped[str] = mapped_column(String(255), nullable=False)
    incorrect_answer3: Mapped[str] = mapped_column(String(255), nullable=False)

    # Metadata
    category: Mapped[str] = mapped_column(String(100), default="Custom")
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Usage stats
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    @property
    def incorrect_answers(self) -> list[str]:
        """Get all incorrect answers as a list."""
        return [self.incorrect_answer1, self.incorrect_answer2, self.incorrect_answer3]

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.times_used == 0:
            return 0.0
        return (self.times_correct / self.times_used) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary format compatible with trivia API."""
        return {
            "question": self.question,
            "correct_answer": self.correct_answer,
            "incorrect_answers": self.incorrect_answers,
            "category": self.category,
            "difficulty": self.difficulty,
        }

    def __repr__(self) -> str:
        return f"<CustomQuestion(id={self.id}, guild={self.guild_id}, category={self.category})>"


class GuildLeaderboard(Base):
    """Cached leaderboard data for guilds."""

    __tablename__ = "guild_leaderboards"
    __table_args__ = (
        UniqueConstraint("guild_id", "leaderboard_type", name="uq_guild_leaderboard_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    leaderboard_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "points", "streak", "accuracy"

    # Cached data (JSON serialized)
    data: Mapped[str] = mapped_column(Text, nullable=False)

    # Cache metadata
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    cache_ttl: Mapped[int] = mapped_column(Integer, default=3600)  # 1 hour in seconds

    @property
    def is_expired(self) -> bool:
        """Check if the cached data has expired."""
        age = datetime.now(UTC) - self.last_updated
        return age.total_seconds() > self.cache_ttl

    def __repr__(self) -> str:
        return f"<GuildLeaderboard(guild={self.guild_id}, type={self.leaderboard_type})>"