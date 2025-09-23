from __future__ import annotations

import logging
from typing import Any

from bot.plugins.base import BasePlugin

from .commands import (
    setup_action_commands,
    setup_channel_commands,
    setup_discipline_commands,
)

logger = logging.getLogger(__name__)


class ModerationPlugin(BasePlugin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self._register_commands()

    def _register_commands(self) -> None:
        command_factories = setup_action_commands(self) + setup_channel_commands(self) + setup_discipline_commands(self)

        for command_func in command_factories:
            setattr(self, command_func.__name__, command_func)
