import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import settings

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.session_factory = None
        self._setup_engine()

    def _setup_engine(self) -> None:
        if self.database_url.startswith("sqlite"):
            # Convert sqlite:/// to sqlite+aiosqlite:///
            async_url = self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
            engine_kwargs = {
                "echo": settings.debug,
                "connect_args": {"check_same_thread": False},
            }
        elif self.database_url.startswith("postgresql"):
            # Convert postgresql:// to postgresql+asyncpg://
            async_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
            engine_kwargs = {
                "echo": settings.debug,
                "pool_size": 20,
                "max_overflow": 30,
                "pool_pre_ping": True,
                "pool_recycle": 300,
            }
        else:
            raise ValueError(f"Unsupported database URL: {self.database_url}")

        self.engine = create_async_engine(async_url, **engine_kwargs)
        self.session_factory = async_sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create_tables(self) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    async def drop_tables(self) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.info("Database tables dropped successfully")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self.session_factory:
            raise RuntimeError("Session factory not initialized")

        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def health_check(self) -> bool:
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def close(self) -> None:
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")


# Global database manager instance
db_manager = DatabaseManager()
