import logging
from typing import TYPE_CHECKING, Any, Type

from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DatabaseMixin:
    """Mixin for plugins that define database models.

    Plugins can inherit from this mixin to register their SQLAlchemy models
    with the database manager for automatic table creation.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._plugin_models: list[Type[DeclarativeBase]] = []

    def register_model(self, model_class: Type[DeclarativeBase]) -> None:
        """Register a model class with this plugin.

        Args:
            model_class: SQLAlchemy model class that inherits from Base
        """
        if not issubclass(model_class, DeclarativeBase):
            raise ValueError(f"Model {model_class.__name__} must inherit from DeclarativeBase")

        if not hasattr(model_class, "__tablename__"):
            raise ValueError(f"Model {model_class.__name__} must define __tablename__")

        self._plugin_models.append(model_class)
        logger.debug(f"Registered model {model_class.__name__} for plugin {getattr(self, 'name', 'unknown')}")

    def register_models(self, *model_classes: Type[DeclarativeBase]) -> None:
        """Register multiple model classes with this plugin.

        Args:
            *model_classes: SQLAlchemy model classes that inherit from Base
        """
        for model_class in model_classes:
            self.register_model(model_class)

    def get_models(self) -> list[Type[DeclarativeBase]]:
        """Get all registered models for this plugin.

        Returns:
            List of registered model classes
        """
        return self._plugin_models.copy()

    async def on_load(self) -> None:
        """Override to register models during plugin load."""
        # Register models with the database manager
        if hasattr(self, 'bot') and hasattr(self.bot, 'db'):
            for model_class in self._plugin_models:
                self.bot.db.register_plugin_model(model_class, getattr(self, 'name', 'unknown'))

        await super().on_load()

    async def on_unload(self) -> None:
        """Override to unregister models during plugin unload."""
        # Unregister models from the database manager
        if hasattr(self, 'bot') and hasattr(self.bot, 'db'):
            for model_class in self._plugin_models:
                self.bot.db.unregister_plugin_model(model_class, getattr(self, 'name', 'unknown'))

        await super().on_unload()