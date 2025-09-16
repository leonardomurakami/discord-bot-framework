"""Command system for Discord bot plugins."""

from .argument_types import CommandArgument
from .decorators import command
from .parsers import ArgumentParserFactory
from .registry import CommandRegistry

__all__ = ["CommandArgument", "command", "CommandRegistry", "ArgumentParserFactory"]
