"""Command registration system."""

import logging
from typing import Any

import hikari
import lightbulb

from .argument_types import CommandArgument
from .parsers import ArgumentParserFactory

logger = logging.getLogger(__name__)


class OptionDescriptorFactory:
    """Factory for creating lightbulb option descriptors."""

    @staticmethod
    def create(arg_def: CommandArgument) -> Any:
        """Create the appropriate lightbulb option descriptor for an argument."""
        # Prepare kwargs, only include choices if not None
        kwargs = {}
        if not arg_def.required:
            kwargs["default"] = (
                arg_def.default if arg_def.default is not None else hikari.UNDEFINED
            )
        if arg_def.choices is not None:
            kwargs["choices"] = arg_def.choices

        # Map option types to lightbulb descriptors
        option_mapping = {
            hikari.OptionType.STRING: lightbulb.string,
            hikari.OptionType.INTEGER: lightbulb.integer,
            hikari.OptionType.USER: lightbulb.user,
            hikari.OptionType.CHANNEL: lightbulb.channel,
            hikari.OptionType.ROLE: lightbulb.role,
            hikari.OptionType.MENTIONABLE: lightbulb.mentionable,
            hikari.OptionType.ATTACHMENT: lightbulb.attachment,
        }

        # Boolean doesn't support choices
        if arg_def.arg_type == hikari.OptionType.BOOLEAN:
            bool_kwargs = {}
            if not arg_def.required:
                bool_kwargs["default"] = (
                    arg_def.default if arg_def.default is not None else hikari.UNDEFINED
                )
            return lightbulb.boolean(arg_def.name, arg_def.description, **bool_kwargs)

        # Types that don't support choices
        no_choices_types = {
            hikari.OptionType.USER,
            hikari.OptionType.CHANNEL,
            hikari.OptionType.ROLE,
            hikari.OptionType.MENTIONABLE,
            hikari.OptionType.ATTACHMENT,
        }

        if arg_def.arg_type in no_choices_types:
            # Remove choices from kwargs for these types
            clean_kwargs = {k: v for k, v in kwargs.items() if k != "choices"}
            descriptor_func = option_mapping.get(arg_def.arg_type, lightbulb.string)
            return descriptor_func(arg_def.name, arg_def.description, **clean_kwargs)

        # Default handling
        descriptor_func = option_mapping.get(arg_def.arg_type, lightbulb.string)
        return descriptor_func(arg_def.name, arg_def.description, **kwargs)


class CommandRegistry:
    """Handles command registration for plugins."""

    def __init__(self, plugin: Any):
        self.plugin = plugin
        self.bot = plugin.bot
        self.logger = logging.getLogger(f"registry.{plugin.name}")
        self._commands: list[Any] = []

    async def register_commands(self) -> None:
        """Register all commands found in the plugin."""
        await self._register_slash_commands()
        await self._register_prefix_commands()

    async def unregister_commands(self) -> None:
        """Unregister all commands."""
        for command in self._commands[
            :
        ]:  # Create a copy to avoid modification during iteration
            try:
                if hasattr(command, "_unified_command"):
                    # Lightbulb commands are cleaned up when the plugin is unloaded
                    cmd_name = command._unified_command["name"]
                    self.logger.debug(
                        f"Lightbulb command {cmd_name} will be cleaned up on plugin unload"
                    )

                if hasattr(command, "_prefix_command"):
                    # Remove prefix command
                    self.bot.message_handler.remove_command(
                        command._prefix_command["name"]
                    )
                    self.logger.debug(
                        f"Removed prefix command: {command._prefix_command['name']}"
                    )

            except Exception as e:
                self.logger.error(f"Error unregistering command: {e}")

        self._commands.clear()

    async def _register_slash_commands(self) -> None:
        """Register slash commands with lightbulb."""
        for attr_name in dir(self.plugin):
            attr = getattr(self.plugin, attr_name)

            if not hasattr(attr, "_unified_command"):
                continue

            try:
                cmd_meta = attr._unified_command

                # Skip if this is prefix-only
                if cmd_meta.get("prefix_only", False):
                    continue

                # Apply permission decorator if needed
                invoke_method = attr
                if cmd_meta.get("permission_node"):
                    from ...permissions import requires_permission

                    invoke_method = requires_permission(cmd_meta["permission_node"])(
                        invoke_method
                    )

                # Create dynamic SlashCommand subclass
                cmd_class_name = f"{cmd_meta['name'].title().replace('-', '').replace('_', '')}Command"
                command_args = cmd_meta.get("arguments", [])

                # Create the invoke method with argument parsing
                async def invoke_wrapper(cmd_instance, ctx):
                    # Extract arguments from context options
                    kwargs = {}
                    if command_args and hasattr(ctx, "options"):
                        for arg_def in command_args:
                            value = getattr(ctx.options, arg_def.name, arg_def.default)
                            kwargs[arg_def.name] = value

                    # Call original method with parsed arguments
                    if kwargs:
                        return await invoke_method(ctx, **kwargs)
                    else:
                        return await invoke_method(ctx)

                # Create command class attributes
                class_attrs = {
                    "invoke": lightbulb.invoke(invoke_wrapper),
                    **cmd_meta.get("lightbulb_kwargs", {}),
                }

                # Create the command class
                cmd_class = type(
                    cmd_class_name,
                    (lightbulb.SlashCommand,),
                    class_attrs,
                    name=cmd_meta["name"],
                    description=cmd_meta["description"],
                )

                # Add option descriptors as class attributes
                if command_args:
                    for arg_def in command_args:
                        option_descriptor = OptionDescriptorFactory.create(arg_def)
                        setattr(cmd_class, arg_def.name, option_descriptor)

                # Register with lightbulb
                self.bot.bot.register(cmd_class)
                self._commands.append(attr)
                self.logger.info(
                    f"Registered slash command: {cmd_meta['name']} from plugin {self.plugin.name}"
                )

            except Exception as e:
                self.logger.error(f"Failed to register slash command {attr_name}: {e}")

    async def _register_prefix_commands(self) -> None:
        """Register prefix commands with the message handler."""
        for attr_name in dir(self.plugin):
            attr = getattr(self.plugin, attr_name)

            if not hasattr(attr, "_prefix_command"):
                continue

            try:
                from ...core.message_handler import PrefixCommand

                original_callback = attr
                prefix_meta = attr._prefix_command
                command_args = prefix_meta.get("arguments", [])

                # Create wrapper function for argument parsing
                prefix_wrapper = self._create_prefix_wrapper(
                    original_callback, prefix_meta, command_args
                )

                prefix_cmd = PrefixCommand(
                    name=prefix_meta["name"],
                    callback=prefix_wrapper,
                    description=prefix_meta.get("description", ""),
                    aliases=prefix_meta.get("aliases", []),
                    permission_node=prefix_meta.get("permission_node"),
                    plugin_name=self.plugin.name,
                    arguments=command_args,
                )
                self.bot.message_handler.add_command(prefix_cmd)
                if attr not in self._commands:  # Avoid duplicates
                    self._commands.append(attr)
                self.logger.info(
                    f"Registered prefix command: {prefix_meta['name']} from plugin {self.plugin.name}"
                )

            except Exception as e:
                self.logger.error(f"Failed to register prefix command {attr_name}: {e}")

    def _create_prefix_wrapper(
        self, callback: Any, meta: dict[str, Any], args: list[CommandArgument]
    ):
        """Create a wrapper function for prefix command argument parsing."""

        async def prefix_wrapper(ctx):
            # Parse arguments based on command definition
            if args and hasattr(ctx, "args"):
                guild_id = getattr(ctx, "guild_id", 0) or 0
                parsed_args = await ArgumentParserFactory.parse_arguments(
                    ctx.args, args, self.bot, guild_id
                )

                # Apply permission check if needed
                if meta.get("permission_node"):
                    from ...permissions import requires_permission

                    wrapped_callback = requires_permission(meta["permission_node"])(
                        callback
                    )
                    return await wrapped_callback(ctx, **parsed_args)
                else:
                    return await callback(ctx, **parsed_args)
            else:
                # No arguments or old-style command
                if meta.get("permission_node"):
                    from ...permissions import requires_permission

                    wrapped_callback = requires_permission(meta["permission_node"])(
                        callback
                    )
                    return await wrapped_callback(ctx)
                else:
                    return await callback(ctx)

        return prefix_wrapper
