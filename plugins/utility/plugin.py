from __future__ import annotations

import logging
from typing import Any

import aiohttp

from bot.plugins.base import BasePlugin

from .commands import setup_convert_commands, setup_info_commands, setup_tool_commands
from .utils import rgb_to_hsl as _rgb_to_hsl_util

logger = logging.getLogger(__name__)


class UtilityPlugin(BasePlugin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession | None = None
        self._register_commands()

    async def on_load(self) -> None:
        self.session = aiohttp.ClientSession()
        await super().on_load()

    async def on_unload(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
        await super().on_unload()

    def _register_commands(self) -> None:
        command_factories = setup_info_commands(self) + setup_convert_commands(self) + setup_tool_commands(self)

        for command_func in command_factories:
            setattr(self, command_func.__name__, command_func)

    @staticmethod
    def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[int, int, int]:
        """Backward-compatibility helper for tests expecting this method."""
        return _rgb_to_hsl_util(r, g, b)
