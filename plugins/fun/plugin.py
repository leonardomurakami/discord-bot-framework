from __future__ import annotations

import logging
from typing import Any

import aiohttp
from fastapi import FastAPI

from bot.plugins.base import BasePlugin
from bot.web.mixins import WebPanelMixin

from .commands import setup_basic_commands, setup_content_commands, setup_game_commands

logger = logging.getLogger(__name__)


class FunPlugin(BasePlugin, WebPanelMixin):
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
        commands = setup_basic_commands(self) + setup_game_commands(self) + setup_content_commands(self)

        for command_func in commands:
            setattr(self, command_func.__name__, command_func)

    # Web Panel Implementation
    def get_panel_info(self) -> dict[str, Any]:
        """Return metadata about this plugin's web panel."""
        return {
            "name": "Fun & Games",
            "description": "Interactive fun commands and games panel",
            "route": "/plugin/fun",
            "icon": "fa-solid fa-gamepad",
            "nav_order": 10,
        }

    def register_web_routes(self, app: FastAPI) -> None:
        """Register web routes for the fun plugin."""
        from .web import register_fun_routes

        register_fun_routes(app, self)
