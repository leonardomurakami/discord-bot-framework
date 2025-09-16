"""Command system for Discord bot plugins."""

from .argument_types import CommandArgument
from .decorators import command
from .registry import CommandRegistry
from .parsers import ArgumentParserFactory

__all__ = ['CommandArgument', 'command', 'CommandRegistry', 'ArgumentParserFactory']
