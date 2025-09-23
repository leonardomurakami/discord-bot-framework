from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models import Base


class MusicQueue(Base):
    __tablename__ = "music_queues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id"))
    position: Mapped[int] = mapped_column(Integer)
    track_identifier: Mapped[str] = mapped_column(String(255))
    track_title: Mapped[str] = mapped_column(String(255))
    track_author: Mapped[str] = mapped_column(String(255))
    track_duration: Mapped[int] = mapped_column(Integer)
    track_uri: Mapped[str] = mapped_column(Text)
    requester_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_guild_position", "guild_id", "position"),
        UniqueConstraint("guild_id", "position"),
    )


class MusicSession(Base):
    __tablename__ = "music_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id"), unique=True)
    voice_channel_id: Mapped[int] = mapped_column(BigInteger)
    text_channel_id: Mapped[int] = mapped_column(BigInteger)
    is_playing: Mapped[bool] = mapped_column(Boolean, default=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    volume: Mapped[int] = mapped_column(Integer, default=50)
    repeat_mode: Mapped[str] = mapped_column(String(10), default="off")  # off, track, queue
    shuffle_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    current_track_position: Mapped[int] = mapped_column(Integer, default=0)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("idx_last_activity", "last_activity"),)


__all__ = ["MusicQueue", "MusicSession"]
