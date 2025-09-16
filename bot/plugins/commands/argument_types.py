"""Command argument types and definitions."""

from dataclasses import dataclass
from typing import Any

import hikari


@dataclass
class CommandArgument:
    """Defines an argument for a command using hikari option types."""

    name: str
    arg_type: hikari.OptionType
    description: str
    required: bool = True
    default: Any = None
    choices: list[Any] | None = None

    def __post_init__(self):
        if not self.required and self.default is None:
            # Set appropriate defaults based on type
            if self.arg_type == hikari.OptionType.STRING:
                self.default = ""
            elif self.arg_type == hikari.OptionType.INTEGER:
                self.default = 0
            elif self.arg_type == hikari.OptionType.BOOLEAN:
                self.default = False
            else:
                self.default = None
