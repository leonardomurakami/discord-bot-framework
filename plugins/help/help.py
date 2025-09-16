import logging
from typing import Dict, Any, List, Optional
import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

logger = logging.getLogger(__name__)


class HelpPlugin(BasePlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Help",
            "version": "1.0.0",
            "author": "Bot Framework",
            "description": "Comprehensive help system showing commands and usage information",
            "permissions": ["help.commands", "help.plugins"],
        }

    @command(
        name="help",
        description="Show help information for commands and plugins",
        aliases=["h"],
        arguments=[
            CommandArgument("query", hikari.OptionType.STRING, "Command name, plugin name, or category to get help for", required=False)
        ]
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
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
            else:
                # Show general help
                help_embed = await self._get_general_help()
                await ctx.respond(embed=help_embed)
            
            await self.log_command_usage(ctx, "help", True)
        
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            embed = self.create_embed(
                title="❌ Help Error",
                description="Failed to retrieve help information. Please try again later.",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "help", False, str(e))

    @command(
        name="commands",
        description="List all available commands organized by plugin",
        aliases=["cmds"],
        permission_node="help.commands"
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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "commands", False, str(e))

    @command(
        name="plugins",
        description="List all loaded plugins with their information",
        aliases=["plugin-list"],
        permission_node="help.plugins"
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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "plugins", False, str(e))

    async def _get_general_help(self) -> hikari.Embed:
        """Generate the main help embed."""
        embed = self.create_embed(
            title="🤖 Bot Help",
            description="Welcome! Here's how to use this bot:",
            color=hikari.Color(0x7289DA)
        )

        # Get basic statistics
        plugin_count = len(self.bot.plugin_loader.get_loaded_plugins())
        prefix_commands = len(self.bot.message_handler.commands)
        
        # Count unique slash commands (lightbulb commands)
        slash_commands = 0
        if hasattr(self.bot.bot, '_slash_commands'):
            slash_commands = len(self.bot.bot._slash_commands)
        
        embed.add_field(
            "📊 Statistics",
            f"• **{plugin_count}** loaded plugins\n• **{prefix_commands}** prefix commands\n• **{slash_commands}** slash commands",
            inline=True
        )
        
        embed.add_field(
            "🎯 Quick Commands",
            f"• `help <command>` - Get help for a specific command\n• `help <plugin>` - Get help for a plugin\n• `commands` - List all commands\n• `plugins` - List all plugins",
            inline=True
        )
        
        embed.add_field(
            "⚙️ Usage",
            f"• **Prefix commands**: `{self.bot.message_handler.prefix}<command>`\n• **Slash commands**: `/<command>`\n• **Both work**: Most commands support both formats!",
            inline=False
        )

        # Add some popular commands if available
        popular_commands = []
        if 'ping' in self.bot.message_handler.commands:
            popular_commands.append("`ping` - Test bot responsiveness")
        if 'roll' in self.bot.message_handler.commands:
            popular_commands.append("`roll` - Roll dice")
        if 'info' in self.bot.message_handler.commands or 'bot-info' in self.bot.message_handler.commands:
            popular_commands.append("`bot-info` - Bot information")
        
        if popular_commands:
            embed.add_field(
                "⭐ Popular Commands",
                "\n".join(popular_commands[:5]),  # Show max 5
                inline=False
            )

        embed.set_footer("💡 Tip: Use 'help <command>' for detailed usage information!")
        return embed

    async def _get_command_help(self, command_name: str) -> Optional[hikari.Embed]:
        """Get detailed help for a specific command."""
        # Check prefix commands first
        prefix_cmd = self.bot.message_handler.commands.get(command_name)
        if prefix_cmd:
            embed = self.create_embed(
                title=f"📖 Help: {prefix_cmd.name}",
                description=prefix_cmd.description or "No description available.",
                color=hikari.Color(0x00FF7F)
            )
            
            embed.add_field(
                "Usage",
                f"`{self.bot.message_handler.prefix}{prefix_cmd.name}`",
                inline=True
            )
            
            if prefix_cmd.aliases:
                aliases = ", ".join([f"`{alias}`" for alias in prefix_cmd.aliases])
                embed.add_field("Aliases", aliases, inline=True)
            
            if prefix_cmd.permission_node:
                embed.add_field(
                    "Required Permission", 
                    f"`{prefix_cmd.permission_node}`", 
                    inline=True
                )
            
            return embed
        
        # TODO: Add slash command help lookup when needed
        return None

    async def _get_plugin_help(self, plugin_name: str) -> Optional[hikari.Embed]:
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
            color=hikari.Color(0x9932CC)
        )
        
        embed.add_field("Version", plugin_info.version, inline=True)
        embed.add_field("Author", plugin_info.author, inline=True)
        
        # Find commands from this plugin
        plugin_commands = []
        for cmd_name, cmd in self.bot.message_handler.commands.items():
            # Try to determine if this command belongs to the plugin
            # This is a simplified check - in a real implementation you might want
            # to track which plugin registered which command
            if hasattr(cmd, 'plugin_name') and cmd.plugin_name.lower() == plugin_name:
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
            color=hikari.Color(0x00CED1)
        )
        
        # Group commands by plugin (simplified grouping)
        command_groups: Dict[str, List[str]] = {}
        
        for cmd_name, cmd in self.bot.message_handler.commands.items():
            # Skip aliases (only show main command names)
            if cmd.name != cmd_name:
                continue
                
            # Try to categorize commands by common patterns
            if cmd_name in ['help', 'commands', 'plugins']:
                group = "Help"
            elif cmd_name in ['ping', 'roll', 'coinflip', '8ball', 'joke', 'choose']:
                group = "Fun"
            elif cmd_name in ['reload', 'plugins', 'permission', 'bot-info']:
                group = "Admin"
            elif cmd_name in ['ban', 'kick', 'mute', 'warn']:
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
            color=hikari.Color(0xFF6B35)
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
                    inline=False
                )
            else:
                embed.add_field(
                    plugin_name,
                    "No metadata available.",
                    inline=False
                )
        
        embed.set_footer("💡 Use 'help <plugin>' for detailed information about any plugin!")
        return embed
