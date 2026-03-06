from __future__ import annotations

import json
from datetime import UTC, date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models import Base


class AngleGame(Base):
    """Track a single daily angle game session per user per guild."""

    __tablename__ = "angle_games"
    __table_args__ = (
        UniqueConstraint("user_id", "guild_id", "game_date", name="uq_angle_game_user_guild_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    target_angle: Mapped[int] = mapped_column(Integer, nullable=False)
    guesses_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    won: Mapped[bool] = mapped_column(Boolean, default=False)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    points_eligible: Mapped[bool] = mapped_column(Boolean, default=True)  # False after first play of the day

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    @property
    def guesses(self) -> list[int]:
        return json.loads(self.guesses_json)

    @guesses.setter
    def guesses(self, value: list[int]) -> None:
        self.guesses_json = json.dumps(value)

    @property
    def attempts_used(self) -> int:
        return len(self.guesses)

    def __repr__(self) -> str:
        return f"<AngleGame(user={self.user_id}, date={self.game_date}, target={self.target_angle})>"


class AngleStats(Base):
    """Persistent angle game statistics per user per guild."""

    __tablename__ = "angle_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "guild_id", name="uq_angle_stats_user_guild"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    total_games: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    total_points: Mapped[int] = mapped_column(Integer, default=0)

    exact_wins: Mapped[int] = mapped_column(Integer, default=0)    # Guessed on first try exactly
    close_wins: Mapped[int] = mapped_column(Integer, default=0)    # Won with 1-2° off

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
        return f"<AngleStats(user={self.user_id}, guild={self.guild_id}, wins={self.wins}/{self.total_games})>"
