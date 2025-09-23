from __future__ import annotations

import logging
from typing import Any

from bot.plugins.base import BasePlugin
from bot.plugins.mixins import DatabaseMixin

from .commands import DefaultLinkCommands, LinkCommands
from .config import links_settings
from .models import Link

logger = logging.getLogger(__name__)


class LinksPlugin(DatabaseMixin, BasePlugin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self._default_links = links_settings.default_links
        # Register the Link model with the database manager
        self.register_model(Link)

        # Initialize command handlers
        self._link_commands = LinkCommands(self)
        self._default_link_commands = DefaultLinkCommands(self)

    async def on_load(self) -> None:
        await super().on_load()
        logger.info("Links plugin loaded")

    async def on_unload(self) -> None:
        await super().on_unload()
        logger.info("Links plugin unloaded")
