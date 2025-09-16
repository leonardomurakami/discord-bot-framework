import logging

import hikari
import lightbulb
import miru

from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command

# Plugin metadata for the loader
PLUGIN_METADATA = {
    "name": "Help",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Comprehensive help system showing commands and usage information with interactive plugin exploration",
    "permissions": ["help.commands", "help.plugins"],
}

logger = logging.getLogger(__name__)


class PersistentPluginSelectView(miru.View):
    """Persistent view for plugin selection that survives bot restarts."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(timeout=None, *args, **kwargs)
        self._setup_select_menu()

    def _setup_select_menu(self) -> None:
        """Setup a placeholder select menu - will be updated when used."""
        # This is just a placeholder that will be replaced when the view is actually used
        select = miru.TextSelect(
            placeholder="Loading plugins...",
            options=[miru.SelectOption(label="Loading...", value="loading")],
            custom_id="help_plugin_select",
        )
        select.callback = self.on_plugin_select
        self.add_item(select)

    async def on_plugin_select(self, ctx: miru.ViewContext) -> None:
        """Handle plugin selection - this will be called even after bot restart."""
        try:
            # Find the help plugin instance through multiple approaches
            help_plugin_instance = None

            # Method 1: Try through the global bot instance reference (most reliable)
            try:
                # Import here to avoid circular imports
                from bot.permissions.decorators import _bot_instance

                if _bot_instance and hasattr(_bot_instance, "plugin_loader"):
                    help_plugin_instance = _bot_instance.plugin_loader.plugins.get("help")
            except (ImportError, AttributeError):
                pass

            # Method 2: Try through miru client's app reference
            if not help_plugin_instance and hasattr(ctx.client, "app"):
                bot_app = ctx.client.app
                if hasattr(bot_app, "plugin_loader") and hasattr(bot_app.plugin_loader, "plugins"):
                    help_plugin_instance = bot_app.plugin_loader.plugins.get("help")

            # Method 3: Try through context bot reference
            if not help_plugin_instance and hasattr(ctx, "bot"):
                bot_instance = ctx.bot
                if hasattr(bot_instance, "plugin_loader") and hasattr(bot_instance.plugin_loader, "plugins"):
                    help_plugin_instance = bot_instance.plugin_loader.plugins.get("help")

            # Debug logging
            logger.debug("Looking for help plugin instance...")
            logger.debug(f"Found help plugin: {help_plugin_instance}")

            if not help_plugin_instance:
                await ctx.respond(
                    "Help system temporarily unavailable. Please try using the help command again.",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            # Handle the selection using the help plugin
            select = None
            for item in self.children:
                if isinstance(item, miru.TextSelect) and item.custom_id == "help_plugin_select":
                    select = item
                    break

            if not select or not select.values:
                return

            selected_value = select.values[0]

            if selected_value == "loading":
                await ctx.respond(
                    "Please wait for the help system to fully load.",
                    flags=hikari.MessageFlag.EPHEMERAL,
                )
                return

            # Handle "Home" selection
            if selected_value == "__home__":
                home_embed = await help_plugin_instance._get_general_help()
                # Update the view with current plugin options
                new_view = PluginSelectView(help_plugin_instance)
                await ctx.edit_response(embed=home_embed, components=new_view)
                return

            # Generate plugin-specific embed
            plugin_embed = await help_plugin_instance._get_plugin_commands_embed(selected_value)

            if plugin_embed:
                # Update the view with current plugin options
                new_view = PluginSelectView(help_plugin_instance)
                await ctx.edit_response(embed=plugin_embed, components=new_view)
            else:
                error_embed = help_plugin_instance.create_embed(
                    title="❌ Plugin Not Found",
                    description=f"Could not find information for plugin: {selected_value}",
                    color=hikari.Color(0xFF0000),
                )
                new_view = PluginSelectView(help_plugin_instance)
                await ctx.edit_response(embed=error_embed, components=new_view)

        except Exception as e:
            logger.error(f"Error in persistent view callback: {e}")
            await ctx.respond(
                "An error occurred while processing your request.",
                flags=hikari.MessageFlag.EPHEMERAL,
            )


class PluginSelectView(miru.View):
    def __init__(self, help_plugin: "HelpPlugin", *args, **kwargs) -> None:
        # Make the view persistent by setting timeout=None
        super().__init__(timeout=None, *args, **kwargs)
        self.help_plugin = help_plugin
        self._setup_select_menu()

    def _setup_select_menu(self) -> None:
        """Setup the plugin selection dropdown menu."""
        try:
            plugins = self.help_plugin.bot.plugin_loader.get_loaded_plugins()
        except (AttributeError, TypeError):
            # Handle case where plugin_loader is None or doesn't have get_loaded_plugins
            return

        if not plugins:
            return

        options = [
            # Add "Home" option first
            miru.SelectOption(
                label="🏠 General Help",
                value="__home__",
                description="Return to the main help overview",
                emoji="🏠",
            )
        ]

        for plugin_name in sorted(plugins):
            try:
                plugin_info = self.help_plugin.bot.plugin_loader.get_plugin_info(plugin_name)
                if plugin_info:
                    description = plugin_info.description[:100] if plugin_info.description else "No description"
                    options.append(
                        miru.SelectOption(
                            label=plugin_info.name,
                            value=plugin_name,
                            description=description,
                            emoji="🔌",
                        )
                    )
            except (AttributeError, TypeError):
                # Handle case where plugin_info is None or invalid
                continue

        if len(options) > 1:  # Only add if we have actual plugins plus home
            select = miru.TextSelect(
                placeholder="Select a plugin to view commands or return home...",
                options=options[:25],  # Discord limit
                custom_id="help_plugin_select",  # Unique custom_id for persistence
            )
            select.callback = self.on_plugin_select
            self.add_item(select)

    async def on_plugin_select(self, ctx: miru.ViewContext) -> None:
        """Handle plugin selection from dropdown - update the original embed."""
        # Get the select component that triggered this callback
        select = None
        for item in self.children:
            if isinstance(item, miru.TextSelect) and item.custom_id == "help_plugin_select":
                select = item
                break

        if not select or not select.values:
            return

        selected_value = select.values[0]

        # Handle "Home" selection
        if selected_value == "__home__":
            home_embed = await self.help_plugin._get_general_help()
            await ctx.edit_response(embed=home_embed, components=self)
            return

        # Generate plugin-specific embed with commands
        plugin_embed = await self.help_plugin._get_plugin_commands_embed(selected_value)

        if plugin_embed:
            # Update the original message with the new embed, keeping the dropdown
            await ctx.edit_response(embed=plugin_embed, components=self)
        else:
            # Show error but keep the dropdown
            error_embed = self.help_plugin.create_embed(
                title="❌ Plugin Not Found",
                description=f"Could not find information for plugin: {selected_value}",
                color=hikari.Color(0xFF0000),
            )
            await ctx.edit_response(embed=error_embed, components=self)


class HelpPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        self._persistent_view_registered = False

    async def on_load(self) -> None:
        """Register persistent views on plugin load."""
        await super().on_load()
        await self._register_persistent_views()

    async def _register_persistent_views(self) -> None:
        """Register persistent help views with miru client."""
        if self._persistent_view_registered:
            return

        miru_client = getattr(self.bot, "miru_client", None)
        if miru_client:
            # Create and register the persistent view
            persistent_view = PersistentPluginSelectView()
            miru_client.start_view(persistent_view, bind_to=None)
            self._persistent_view_registered = True
            self.logger.info("Registered persistent help view")

    @command(
        name="help",
        description="Show help information for commands and plugins",
        aliases=["h"],
        arguments=[
            CommandArgument(
                "query",
                hikari.OptionType.STRING,
                "Command name, plugin name, or category to get help for",
                required=False,
            )
        ],
    )
    async def help_command(self, ctx: lightbulb.Context, query: str = None) -> None:
        """Main help command that provides comprehensive help information."""
        try:
            if query:
                # Show specific help for command or plugin
                query = query.lower().strip()

                # First, try to find a specific command
                command_help = await self._get_command_help(query)
                if command_help:
                    await ctx.respond(embed=command_help)
                    await self.log_command_usage(ctx, "help", True)
                    return

                # Then try to find a plugin
                plugin_help = await self._get_plugin_help(query)
                if plugin_help:
                    await ctx.respond(embed=plugin_help)
                    await self.log_command_usage(ctx, "help", True)
                    return

                # Nothing found
                embed = self.create_embed(
                    title="❌ Help Not Found",
                    description=f"No help found for `{query}`. Use `help` without arguments to see all available commands.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
            else:
                # Show general help with plugin dropdown
                help_embed = await self._get_general_help()
                view = PluginSelectView(self)

                # Check if miru client is available
                miru_client = getattr(self.bot, "miru_client", None)
                if miru_client and view.children:
                    await ctx.respond(embed=help_embed, components=view)
                    miru_client.start_view(view)
                else:
                    await ctx.respond(embed=help_embed)

            await self.log_command_usage(ctx, "help", True)

        except Exception as e:
            logger.error(f"Error in help command: {e}")
            embed = self.create_embed(
                title="❌ Help Error",
                description="Failed to retrieve help information. Please try again later.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "help", False, str(e))

    @command(
        name="commands",
        description="List all available commands organized by plugin",
        aliases=["cmds"],
        permission_node="help.commands",
    )
    async def list_commands(self, ctx: lightbulb.Context) -> None:
        """List all available commands organized by plugin."""
        try:
            embed = await self._get_commands_list()
            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "commands", True)

        except Exception as e:
            logger.error(f"Error in commands command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to retrieve commands list.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "commands", False, str(e))

    @command(
        name="plugins",
        description="List all loaded plugins with their information",
        aliases=["plugin-list"],
        permission_node="help.plugins",
    )
    async def list_plugins(self, ctx: lightbulb.Context) -> None:
        """List all loaded plugins with their information."""
        try:
            embed = await self._get_plugins_list()
            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "plugins", True)

        except Exception as e:
            logger.error(f"Error in plugins command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to retrieve plugins list.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "plugins", False, str(e))

    async def _get_general_help(self) -> hikari.Embed:
        """Generate the main help embed with improved design."""
        embed = self.create_embed(
            title="🚀 Welcome to the Bot!",
            description="Your complete assistant for Discord server management and fun activities.",
            color=hikari.Color(0x5865F2),  # Discord's brand color
        )

        # Get basic statistics with error handling
        plugin_count = 0
        try:
            if self.bot.plugin_loader:
                plugin_count = len(self.bot.plugin_loader.get_loaded_plugins())
        except (AttributeError, TypeError):
            pass

        # Count unique commands (excluding aliases)
        unique_commands = 0
        seen_commands = set()
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                for cmd_name, cmd in self.bot.message_handler.commands.items():
                    if cmd.name == cmd_name and cmd.name not in seen_commands:
                        unique_commands += 1
                        seen_commands.add(cmd.name)
        except (AttributeError, TypeError):
            pass

        # Get plugin categories
        plugin_categories = []
        try:
            if self.bot.plugin_loader:
                plugins = self.bot.plugin_loader.get_loaded_plugins()
                for plugin_name in plugins:
                    try:
                        plugin_info = self.bot.plugin_loader.get_plugin_info(plugin_name)
                        if plugin_info:
                            plugin_categories.append(plugin_info.name)
                    except (AttributeError, TypeError):
                        continue
        except (AttributeError, TypeError):
            pass

        # Get prefix safely
        prefix = "!"  # Default prefix
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                prefix = getattr(self.bot.message_handler, "prefix", "!")
        except (AttributeError, TypeError):
            pass

        # Main stats in a more visual way
        embed.add_field(
            "📊 What's Available",
            f"🔌 **{plugin_count}** plugins loaded\n"
            f"⚡ **{unique_commands}** commands ready\n"
            f"🎛️ **Prefix**: `{prefix}` or `/` slash commands",
            inline=True,
        )

        # Getting started section
        embed.add_field(
            "🎯 Getting Started",
            f"• Type `{prefix}help <command>` for specific help\n"
            f"• Use the **dropdown below** to explore plugins\n"
            f"• Try `{prefix}ping` to test the bot\n"
            f"• Most commands work as both prefix and slash!",
            inline=True,
        )

        # Show available plugin categories
        if plugin_categories:
            categories_text = "**Available Categories:**\n"
            # Group into a nice display
            for category in plugin_categories[:6]:  # Show max 6
                categories_text += f"• {category}\n"
            if len(plugin_categories) > 6:
                categories_text += f"• ...and {len(plugin_categories) - 6} more!"

            embed.add_field("🗂️ Plugin Categories", categories_text, inline=False)

        # Popular/essential commands section
        essential_commands = []
        command_suggestions = [
            ("ping", "🏓", "Test bot responsiveness"),
            ("help", "❓", "Show this help menu"),
            ("roll", "🎲", "Roll dice for games"),
            ("info", "ℹ️", "Bot information"),
            ("bot-info", "ℹ️", "Bot information"),
            ("commands", "📋", "List all commands"),
            ("plugins", "🔌", "Show loaded plugins"),
        ]

        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                for cmd_name, emoji, desc in command_suggestions:
                    if cmd_name in self.bot.message_handler.commands:
                        essential_commands.append(f"{emoji} `{prefix}{cmd_name}` - {desc}")
        except (AttributeError, TypeError):
            pass

        if essential_commands:
            embed.add_field("⭐ Essential Commands", "\n".join(essential_commands[:5]), inline=False)

        # Footer with helpful tip
        embed.set_footer(
            text="💡 Pro tip: Use the dropdown menu below to explore different plugin categories!",
            icon=(self.bot.hikari_bot.get_me().make_avatar_url() if self.bot.hikari_bot.get_me() else None),
        )

        return embed

    async def _get_command_help(self, command_name: str) -> hikari.Embed | None:
        """Get detailed help for a specific command."""
        # Get prefix safely
        prefix = "!"  # Default prefix
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                prefix = getattr(self.bot.message_handler, "prefix", "!")
        except (AttributeError, TypeError):
            pass

        # Check prefix commands first
        prefix_cmd = None
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                prefix_cmd = self.bot.message_handler.commands.get(command_name)
        except (AttributeError, TypeError):
            pass

        if prefix_cmd:
            embed = self.create_embed(
                title=f"📖 Help: {prefix_cmd.name}",
                description=prefix_cmd.description or "No description available.",
                color=hikari.Color(0x00FF7F),
            )

            embed.add_field("Usage", f"`{prefix}{prefix_cmd.name}`", inline=True)

            if hasattr(prefix_cmd, "aliases") and prefix_cmd.aliases:
                aliases = ", ".join([f"`{alias}`" for alias in prefix_cmd.aliases])
                embed.add_field("Aliases", aliases, inline=True)

            if hasattr(prefix_cmd, "permission_node") and prefix_cmd.permission_node:
                embed.add_field(
                    "Required Permission",
                    f"`{prefix_cmd.permission_node}`",
                    inline=True,
                )

            return embed

        # TODO: Add slash command help lookup when needed
        return None

    async def _get_plugin_help(self, plugin_name: str) -> hikari.Embed | None:
        """Get help for a specific plugin."""
        # Try to find the plugin
        plugins = self.bot.plugin_loader.get_loaded_plugins()

        # Check if plugin exists (case insensitive)
        found_plugin = None
        for plugin in plugins:
            if plugin.lower() == plugin_name:
                found_plugin = plugin
                break

        if not found_plugin:
            return None

        plugin_info = self.bot.plugin_loader.get_plugin_info(found_plugin)
        if not plugin_info:
            return None

        embed = self.create_embed(
            title=f"🔌 Plugin: {plugin_info.name}",
            description=plugin_info.description or "No description available.",
            color=hikari.Color(0x9932CC),
        )

        embed.add_field("Version", plugin_info.version, inline=True)
        embed.add_field("Author", plugin_info.author, inline=True)

        # Find commands from this plugin
        plugin_commands = []
        for cmd_name, cmd in self.bot.message_handler.commands.items():
            # Try to determine if this command belongs to the plugin
            # This is a simplified check - in a real implementation you might want
            # to track which plugin registered which command
            if hasattr(cmd, "plugin_name") and cmd.plugin_name.lower() == plugin_name:
                plugin_commands.append(cmd_name)

        if plugin_commands:
            commands_list = ", ".join([f"`{cmd}`" for cmd in plugin_commands[:10]])
            if len(plugin_commands) > 10:
                commands_list += f" ... and {len(plugin_commands) - 10} more"
            embed.add_field("Commands", commands_list, inline=False)

        if plugin_info.permissions:
            perms_list = "\n".join([f"• `{perm}`" for perm in plugin_info.permissions[:5]])
            if len(plugin_info.permissions) > 5:
                perms_list += f"\n... and {len(plugin_info.permissions) - 5} more"
            embed.add_field("Permissions", perms_list, inline=False)

        return embed

    async def _get_commands_list(self) -> hikari.Embed:
        """Generate a list of all commands organized by plugin."""
        embed = self.create_embed(
            title="📋 All Commands",
            description="Here are all available commands:",
            color=hikari.Color(0x00CED1),
        )

        # Group commands by plugin (simplified grouping)
        command_groups: dict[str, list[str]] = {}

        for cmd_name, cmd in self.bot.message_handler.commands.items():
            # Skip aliases (only show main command names)
            if cmd.name != cmd_name:
                continue

            # Try to categorize commands by common patterns
            if cmd_name in ["help", "commands", "plugins"]:
                group = "Help"
            elif cmd_name in ["ping", "roll", "coinflip", "8ball", "joke", "choose"]:
                group = "Fun"
            elif cmd_name in ["reload", "plugins", "permission", "bot-info"]:
                group = "Admin"
            elif cmd_name in ["ban", "kick", "mute", "warn"]:
                group = "Moderation"
            else:
                group = "Other"

            if group not in command_groups:
                command_groups[group] = []
            command_groups[group].append(cmd_name)

        # Add fields for each group
        for group, commands in command_groups.items():
            if commands:
                commands_text = ", ".join([f"`{cmd}`" for cmd in sorted(commands)])
                embed.add_field(f"{group}", commands_text, inline=False)

        embed.set_footer("💡 Use 'help <command>' for detailed information about any command!")
        return embed

    async def _get_plugins_list(self) -> hikari.Embed:
        """Generate a list of all loaded plugins."""
        embed = self.create_embed(
            title="🔌 Loaded Plugins",
            description="Here are all currently loaded plugins:",
            color=hikari.Color(0xFF6B35),
        )

        plugins = self.bot.plugin_loader.get_loaded_plugins()

        if not plugins:
            embed.description = "No plugins are currently loaded."
            return embed

        for plugin_name in sorted(plugins):
            plugin_info = self.bot.plugin_loader.get_plugin_info(plugin_name)
            if plugin_info:
                description = plugin_info.description[:100]  # Truncate long descriptions
                if len(plugin_info.description) > 100:
                    description += "..."
                embed.add_field(
                    f"{plugin_info.name} v{plugin_info.version}",
                    description or "No description available.",
                    inline=False,
                )
            else:
                embed.add_field(plugin_name, "No metadata available.", inline=False)

        embed.set_footer("💡 Use 'help <plugin>' for detailed information about any plugin!")
        return embed

    async def _get_plugin_commands_embed(self, plugin_name: str) -> hikari.Embed | None:
        """Generate a user-friendly embed showing all commands for a specific plugin."""
        # Get plugin info
        plugin_info = self.bot.plugin_loader.get_plugin_info(plugin_name)
        if not plugin_info:
            embed = self.create_embed(
                title="❌ Plugin Not Found",
                description=f"Plugin '{plugin_name}' not found",
                color=hikari.Color(0xFF0000),
            )
            return embed

        embed = self.create_embed(
            title=f"🔌 {plugin_info.name} Commands",
            description=plugin_info.description or "No description available.",
            color=hikari.Color(0x9932CC),
        )

        # Add plugin metadata
        embed.add_field("Version", plugin_info.version, inline=True)
        embed.add_field("Author", plugin_info.author, inline=True)
        embed.add_field("Plugin", plugin_name.title(), inline=True)

        # Find commands from this plugin
        prefix_commands = []
        for cmd_name, cmd in self.bot.message_handler.commands.items():
            # Skip aliases (only show main command names)
            if cmd.name != cmd_name:
                continue

            # Check if this command belongs to the plugin
            if hasattr(cmd, "plugin_name") and cmd.plugin_name and cmd.plugin_name.lower() == plugin_name.lower():
                prefix_commands.append(cmd)

        # Display commands in a user-friendly way
        if prefix_commands:
            commands_text = ""
            for cmd in sorted(prefix_commands, key=lambda x: x.name):
                # Get command arguments if available
                cmd_usage = f"`{self.bot.message_handler.prefix}{cmd.name}"

                # Get arguments directly from the command object
                args = getattr(cmd, "arguments", [])

                # Add argument usage if found
                if args:
                    arg_parts = []
                    for arg in args:
                        if arg.required:
                            arg_parts.append(f"<{arg.name}>")
                        else:
                            default_hint = f"={arg.default}" if arg.default is not None and arg.default != "" else ""
                            arg_parts.append(f"[{arg.name}{default_hint}]")
                    if arg_parts:
                        cmd_usage += f" {' '.join(arg_parts)}"

                cmd_usage += "`"

                # Add aliases in a friendlier way
                alias_text = ""
                if cmd.aliases:
                    alias_text = f" (also: {', '.join([f'`{alias}`' for alias in cmd.aliases[:3]])})"
                    if len(cmd.aliases) > 3:
                        alias_text = f" (also: {', '.join([f'`{alias}`' for alias in cmd.aliases[:2]])} + {len(cmd.aliases)-2} more)"

                # Format the command line
                description = cmd.description or "No description available"
                commands_text += f"**{cmd_usage}**{alias_text}\n{description}\n\n"

            if commands_text:
                # Split into multiple fields if too long
                if len(commands_text) > 1024:
                    # Split by commands (double newline separator)
                    command_blocks = commands_text.strip().split("\n\n")
                    current_field = ""
                    field_num = 1

                    for block in command_blocks:
                        if len(current_field + block + "\n\n") > 1024 and current_field:
                            embed.add_field(
                                f"📝 Commands (Part {field_num})",
                                current_field.strip(),
                                inline=False,
                            )
                            current_field = block + "\n\n"
                            field_num += 1
                        else:
                            current_field += block + "\n\n"

                    if current_field.strip():
                        embed.add_field(
                            f"📝 Commands (Part {field_num})",
                            current_field.strip(),
                            inline=False,
                        )
                else:
                    embed.add_field("📝 Commands", commands_text.strip(), inline=False)
        else:
            embed.add_field("📝 Commands", "No commands available in this plugin.", inline=False)

        embed.set_footer("💡 Use the dropdown below to view other plugins!")
        return embed

    async def _get_command_info(self, command_name: str) -> dict | None:
        """Get detailed information for a specific command."""
        # Get prefix safely
        prefix = "!"  # Default prefix
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                prefix = getattr(self.bot.message_handler, "prefix", "!")
        except (AttributeError, TypeError):
            pass

        # Get commands safely
        commands = {}
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                commands = self.bot.message_handler.commands
        except (AttributeError, TypeError):
            pass

        # First check direct command match
        for cmd in commands.values():
            if hasattr(cmd, "name") and cmd.name == command_name:
                return {
                    "name": cmd.name,
                    "description": getattr(cmd, "description", None),
                    "aliases": getattr(cmd, "aliases", []),
                    "permission_node": getattr(cmd, "permission_node", None),
                    "usage": f"{prefix}{cmd.name}",
                    "plugin_name": getattr(cmd, "plugin_name", None),
                }

        # Then check aliases
        for cmd in commands.values():
            if hasattr(cmd, "aliases") and cmd.aliases and command_name in cmd.aliases:
                return {
                    "name": getattr(cmd, "name", "Unknown"),
                    "description": getattr(cmd, "description", None),
                    "aliases": getattr(cmd, "aliases", []),
                    "permission_node": getattr(cmd, "permission_node", None),
                    "usage": f"{prefix}{getattr(cmd, 'name', 'unknown')}",
                    "plugin_name": getattr(cmd, "plugin_name", None),
                }

        return None

    def _format_command_list(self, commands: list[dict]) -> list[str]:
        """Format a list of commands into strings that fit Discord embed field limits."""
        if not commands:
            return ["No commands available."]

        formatted_pages = []
        current_page = ""

        for cmd in commands:
            cmd_name = cmd.get("name", "Unknown")
            cmd_desc = cmd.get("description", "No description")

            cmd_line = f"**{cmd_name}** - {cmd_desc}\n"

            # Check if adding this command would exceed the 1024 character limit
            if len(current_page + cmd_line) > 1000:  # Leave some buffer
                if current_page:
                    formatted_pages.append(current_page.strip())
                current_page = cmd_line
            else:
                current_page += cmd_line

        # Add the last page if it has content
        if current_page.strip():
            formatted_pages.append(current_page.strip())

        return formatted_pages if formatted_pages else ["No commands available."]

    def _get_plugin_overview(self, plugin_name: str, plugin_obj) -> str:
        """Get a brief overview of a plugin for listing purposes."""
        try:
            if hasattr(plugin_obj, "plugin_info"):
                info = plugin_obj.plugin_info
                name = info.get("name", plugin_name.title())
                version = info.get("version", "Unknown")
                author = info.get("author", "Unknown")
                commands = info.get("commands", [])
                cmd_count = len(commands) if commands else 0

                return f"**{name}** v{version} by {author} ({cmd_count} commands)"
            else:
                return f"**{plugin_name.title()}** - No metadata available"
        except Exception:
            return f"**{plugin_name.title()}** - Information unavailable"
