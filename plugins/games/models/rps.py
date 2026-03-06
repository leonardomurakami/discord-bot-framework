from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models import Base


class RPSStats(Base):
    """Persistent Rock-Paper-Scissors statistics per user per guild."""

    __tablename__ = "rps_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "guild_id", name="uq_rps_stats_user_guild"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    total_games: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)

    # Wins broken down by the choice the player used
    rock_wins: Mapped[int] = mapped_column(Integer, default=0)
    paper_wins: Mapped[int] = mapped_column(Integer, default=0)
    scissors_wins: Mapped[int] = mapped_column(Integer, default=0)

    current_win_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_win_streak: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    @property
    def win_rate(self) -> float:
        if self.total_games == 0:
            return 0.0
        return (self.wins / self.total_games) * 100

    def __repr__(self) -> str:
        return f"<RPSStats(user={self.user_id}, guild={self.guild_id}, wins={self.wins}/{self.total_games})>"


class RPSAchievement(Base):
    """An unlocked RPS achievement for a user in a guild."""

    __tablename__ = "rps_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "guild_id", "achievement_id", name="uq_rps_achievement_user_guild_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    achievement_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    def __repr__(self) -> str:
        return f"<RPSAchievement(user={self.user_id}, id={self.achievement_id})>"
