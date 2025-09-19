import logging
from typing import Optional
import hikari

logger = logging.getLogger(__name__)


class EmbedGenerators:
    """Handles all embed generation for the help system."""

    def __init__(self, help_plugin):
        self.help_plugin = help_plugin
        self.bot = help_plugin.bot

    async def get_general_help(self, guild_id: int = None) -> hikari.Embed:
        """Generate the main help embed with improved design."""
        from .command_info import CommandInfoManager

        info_manager = CommandInfoManager(self.help_plugin)

        embed = self.help_plugin.create_embed(
            title="🚀 Welcome to the Bot!",
            description="Your complete assistant for Discord server management and fun activities.",
            color=hikari.Color(0x5865F2),  # Discord's brand color
        )

        # Get basic statistics
        stats = info_manager.get_bot_statistics()
        prefix = await info_manager.get_prefix(guild_id)

        # Main stats in a more visual way
        embed.add_field(
            "📊 What's Available",
            f"🔌 **{stats['plugin_count']}** plugins loaded\n"
            f"⚡ **{stats['unique_commands']}** commands ready\n"
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
        if stats['plugin_categories']:
            categories_text = "**Available Categories:**\n"
            # Group into a nice display
            for category in stats['plugin_categories'][:6]:  # Show max 6
                categories_text += f"• {category}\n"
            if len(stats['plugin_categories']) > 6:
                categories_text += f"• ...and {len(stats['plugin_categories']) - 6} more!"

            embed.add_field("🗂️ Plugin Categories", categories_text, inline=False)

        # Popular/essential commands section
        essential_commands = await info_manager.get_essential_commands(guild_id)
        if essential_commands:
            embed.add_field("⭐ Essential Commands", "\n".join(essential_commands[:5]), inline=False)

        # Footer with helpful tip
        embed.set_footer(
            text="💡 Pro tip: Use the dropdown menu below to explore different plugin categories!",
            icon=(self.bot.hikari_bot.get_me().make_avatar_url() if self.bot.hikari_bot.get_me() else None),
        )

        return embed

    async def get_command_help(self, command_name: str, guild_id: int = None) -> Optional[hikari.Embed]:
        """Get detailed help for a specific command."""
        from .command_info import CommandInfoManager

        info_manager = CommandInfoManager(self.help_plugin)
        prefix = await info_manager.get_prefix(guild_id)

        # Check prefix commands first
        prefix_cmd = None
        try:
            if hasattr(self.bot, "message_handler") and self.bot.message_handler:
                prefix_cmd = self.bot.message_handler.commands.get(command_name)
        except (AttributeError, TypeError):
            pass

        if prefix_cmd:
            embed = self.help_plugin.create_embed(
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

    async def get_plugin_help(self, plugin_name: str) -> Optional[hikari.Embed]:
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

        embed = self.help_plugin.create_embed(
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

    async def get_commands_list(self) -> hikari.Embed:
        """Generate a list of all commands organized by plugin."""
        embed = self.help_plugin.create_embed(
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

    async def get_plugins_list(self) -> hikari.Embed:
        """Generate a list of all loaded plugins."""
        embed = self.help_plugin.create_embed(
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

    async def get_plugin_commands_embed(self, plugin_name: str, guild_id: int = None, page: int = 0) -> Optional[hikari.Embed]:
        """Generate a user-friendly embed showing all commands for a specific plugin."""
        from .command_info import CommandInfoManager

        info_manager = CommandInfoManager(self.help_plugin)

        # Get plugin info
        plugin_info = self.bot.plugin_loader.get_plugin_info(plugin_name)
        if not plugin_info:
            embed = self.help_plugin.create_embed(
                title="❌ Plugin Not Found",
                description=f"Plugin '{plugin_name}' not found",
                color=hikari.Color(0xFF0000),
            )
            return embed

        embed = self.help_plugin.create_embed(
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

        # Display commands in a user-friendly way with pagination
        if prefix_commands:
            prefix = await info_manager.get_prefix(guild_id)

            # Sort commands and paginate (5 commands per page)
            sorted_commands = sorted(prefix_commands, key=lambda x: x.name)
            commands_per_page = 5
            total_pages = (len(sorted_commands) + commands_per_page - 1) // commands_per_page

            # Calculate page bounds
            start_idx = page * commands_per_page
            end_idx = min(start_idx + commands_per_page, len(sorted_commands))
            page_commands = sorted_commands[start_idx:end_idx]

            commands_text = ""

            for cmd in page_commands:
                # Get command arguments if available
                cmd_usage = f"`{prefix}{cmd.name}"

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
                # Add pagination info to field title
                field_title = f"📝 Commands (Page {page + 1}/{total_pages})"
                embed.add_field(field_title, commands_text.strip(), inline=False)

                # Add pagination info to embed footer
                embed.set_footer(f"Showing {len(page_commands)} of {len(sorted_commands)} commands • Page {page + 1}/{total_pages}")

            # Return pagination info separately as a tuple
            return embed, {
                "current_page": page,
                "total_pages": total_pages,
                "plugin_name": plugin_name,
                "guild_id": guild_id,
                "total_commands": len(sorted_commands)
            }
        else:
            embed.add_field("📝 Commands", "No commands available in this plugin.", inline=False)
            # Return tuple for consistency
            return embed, {
                "current_page": 0,
                "total_pages": 1,
                "plugin_name": plugin_name,
                "guild_id": guild_id,
                "total_commands": 0
            }