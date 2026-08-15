from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aiohttp

from bot.plugins.base import BasePlugin
from bot.plugins.mixins import DatabaseMixin
from config.settings import settings

from .commands import setup_chat_commands, setup_clear_commands
from .models import AIConversation

if TYPE_CHECKING:
    from bot.core.bot import DiscordBot

logger = logging.getLogger(__name__)


class AIPlugin(DatabaseMixin, BasePlugin):
    """AI chat plugin backed by the acpbox OpenAI-compatible endpoint."""

    def __init__(self, bot: DiscordBot) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession | None = None
        self.register_model(AIConversation)
        self._register_commands()

    async def on_load(self) -> None:
        # Soft-fail when acpbox is not configured: skip session creation so the
        # bot still starts. Commands will surface a configuration error instead.
        if not settings.acpbox_url:
            logger.warning("AI plugin loaded without ACPBOX_URL; chat commands will return a configuration error until it is set.")
            await super().on_load()
            return

        timeout = aiohttp.ClientTimeout(total=settings.ai_request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("AI plugin loaded successfully (acpbox=%s, model=%s)", settings.acpbox_url, settings.ai_model)
        await super().on_load()

    async def on_unload(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
        await super().on_unload()
        logger.info("AI plugin unloaded")

    def _register_commands(self) -> None:
        commands = setup_chat_commands(self) + setup_clear_commands(self)
        for command_func in commands:
            setattr(self, command_func.__name__, command_func)
