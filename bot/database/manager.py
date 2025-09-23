import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Type

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.session_factory = None
        self._plugin_models: dict[str, list[Type[DeclarativeBase]]] = {}
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

    def register_plugin_model(self, model_class: Type[DeclarativeBase], plugin_name: str) -> None:
        """Register a model class from a plugin.

        Args:
            model_class: SQLAlchemy model class that inherits from Base
            plugin_name: Name of the plugin registering the model
        """
        if not issubclass(model_class, DeclarativeBase):
            raise ValueError(f"Model {model_class.__name__} must inherit from DeclarativeBase")

        if not hasattr(model_class, "__tablename__"):
            raise ValueError(f"Model {model_class.__name__} must define __tablename__")

        if plugin_name not in self._plugin_models:
            self._plugin_models[plugin_name] = []

        if model_class not in self._plugin_models[plugin_name]:
            self._plugin_models[plugin_name].append(model_class)
            logger.debug(f"Registered model {model_class.__name__} for plugin {plugin_name}")

    def unregister_plugin_model(self, model_class: Type[DeclarativeBase], plugin_name: str) -> None:
        """Unregister a model class from a plugin.

        Args:
            model_class: SQLAlchemy model class to unregister
            plugin_name: Name of the plugin unregistering the model
        """
        if plugin_name in self._plugin_models:
            try:
                self._plugin_models[plugin_name].remove(model_class)
                logger.debug(f"Unregistered model {model_class.__name__} for plugin {plugin_name}")

                # Clean up empty plugin entries
                if not self._plugin_models[plugin_name]:
                    del self._plugin_models[plugin_name]
            except ValueError:
                logger.warning(f"Model {model_class.__name__} was not registered for plugin {plugin_name}")

    def get_plugin_models(self, plugin_name: str | None = None) -> list[Type[DeclarativeBase]]:
        """Get registered models for a plugin or all plugins.

        Args:
            plugin_name: Name of plugin to get models for, or None for all models

        Returns:
            List of registered model classes
        """
        if plugin_name:
            return self._plugin_models.get(plugin_name, []).copy()

        # Return all models from all plugins
        all_models = []
        for models in self._plugin_models.values():
            all_models.extend(models)
        return all_models

    async def create_tables(self) -> None:
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        total_models = len(self.get_plugin_models())
        logger.info(f"Database tables created successfully (including {total_models} plugin models)")

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
