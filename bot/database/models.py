from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    prefix: Mapped[str] = mapped_column(String(10), default="!")
    language: Mapped[str] = mapped_column(String(10), default="en")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users: Mapped[list["GuildUser"]] = relationship(back_populates="guild")
    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="guild")
    command_usage: Mapped[list["CommandUsage"]] = relationship(back_populates="guild")
    plugin_settings: Mapped[list["PluginSetting"]] = relationship(back_populates="guild")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(32))
    discriminator: Mapped[str] = mapped_column(String(4))
    global_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    guild_data: Mapped[list["GuildUser"]] = relationship(back_populates="user")
    command_usage: Mapped[list["CommandUsage"]] = relationship(back_populates="user")


class GuildUser(Base):
    __tablename__ = "guild_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    nickname: Mapped[str | None] = mapped_column(String(32))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    guild: Mapped["Guild"] = relationship(back_populates="users")
    user: Mapped["User"] = relationship(back_populates="guild_data")

    __table_args__ = (UniqueConstraint("guild_id", "user_id"),)


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id"))
    role_id: Mapped[int] = mapped_column(BigInteger)
    permission_id: Mapped[int] = mapped_column(Integer, ForeignKey("permissions.id"))
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    guild: Mapped["Guild"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")

    __table_args__ = (
        UniqueConstraint("guild_id", "role_id", "permission_id"),
        Index("idx_guild_role", "guild_id", "role_id"),
    )


class CommandUsage(Base):
    __tablename__ = "command_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    command_name: Mapped[str] = mapped_column(String(100))
    plugin_name: Mapped[str] = mapped_column(String(50))
    success: Mapped[bool] = mapped_column(Boolean)
    error_message: Mapped[str | None] = mapped_column(Text)
    execution_time: Mapped[float | None] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    guild: Mapped["Guild"] = relationship(back_populates="command_usage")
    user: Mapped["User"] = relationship(back_populates="command_usage")

    __table_args__ = (
        Index("idx_guild_command", "guild_id", "command_name"),
        Index("idx_timestamp", "timestamp"),
    )


class PluginSetting(Base):
    __tablename__ = "plugin_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("guilds.id"))
    plugin_name: Mapped[str] = mapped_column(String(50))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    guild: Mapped["Guild"] = relationship(back_populates="plugin_settings")

    __table_args__ = (UniqueConstraint("guild_id", "plugin_name"),)
