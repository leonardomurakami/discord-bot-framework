"""Command decorators for unified command creation."""

from .argument_types import CommandArgument


def command(
    name: str,
    description: str = "",
    aliases: list[str] | None = None,
    permission_node: str | None = None,
    slash_only: bool = False,
    prefix_only: bool = False,
    arguments: list[CommandArgument] | None = None,
    **lightbulb_kwargs,
):
    """
    Unified command decorator that creates both slash and prefix commands.

    This creates command metadata that will be processed during plugin loading.
    """

    def decorator(func):
        # Store command metadata on the function
        func._unified_command = {
            "name": name,
            "description": description,
            "permission_node": permission_node,
            "slash_only": slash_only,
            "prefix_only": prefix_only,
            "arguments": arguments or [],
            "lightbulb_kwargs": lightbulb_kwargs,
        }

        # Create prefix command version (unless slash_only)
        if not slash_only:
            func._prefix_command = {
                "name": name,
                "description": description,
                "aliases": aliases or [],
                "permission_node": permission_node,
                "arguments": arguments or [],
            }

        return func

    return decorator
