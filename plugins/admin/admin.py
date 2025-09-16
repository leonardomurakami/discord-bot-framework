import logging
from typing import Dict, Any
import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

logger = logging.getLogger(__name__)


class AdminPlugin(BasePlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Admin",
            "version": "1.0.0",
            "author": "Bot Framework",
            "description": "Administrative commands for bot management",
            "permissions": ["admin.config", "admin.plugins", "admin.permissions"],
        }

    @command(
        name="reload",
        description="Reload a plugin or all plugins",
        aliases=["reload-plugin"],
        permission_node="admin.plugins"
    )
    async def reload_plugin(self, ctx: lightbulb.Context) -> None:
        # For prefix commands, get plugin from args; for slash commands, from options
        if hasattr(ctx, 'options') and hasattr(ctx.options, 'plugin'):
            plugin = ctx.options.plugin
        elif hasattr(ctx, 'args') and ctx.args:
            plugin = ctx.args[0] if ctx.args else None
        else:
            plugin = None
        start_time = hikari.utcnow()

        try:
            if plugin == "all" or plugin is None:
                await self.bot.plugin_loader.reload_all_plugins()
                embed = self.create_embed(
                    title="✅ Plugin Reload",
                    description="All plugins have been reloaded successfully!",
                    color=hikari.Color(0x00FF00)
                )
            else:
                success = await self.bot.plugin_loader.reload_plugin(plugin)
                if success:
                    embed = self.create_embed(
                        title="✅ Plugin Reload",
                        description=f"Plugin `{plugin}` has been reloaded successfully!",
                        color=hikari.Color(0x00FF00)
                    )
                else:
                    embed = self.create_embed(
                        title="❌ Plugin Reload Failed",
                        description=f"Failed to reload plugin `{plugin}`. Check logs for details.",
                        color=hikari.Color(0xFF0000)
                    )

            await ctx.respond(embed=embed)

            # Log command usage
            execution_time = (hikari.utcnow() - start_time).total_seconds()
            await self.log_command_usage(ctx, "reload", True, execution_time=execution_time)

        except Exception as e:
            logger.error(f"Error in reload command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)

            execution_time = (hikari.utcnow() - start_time).total_seconds()
            await self.log_command_usage(ctx, "reload", False, str(e), execution_time)

    @command(
        name="plugins",
        description="List all loaded plugins and their status",
        aliases=["list-plugins"],
        permission_node="admin.plugins"
    )
    async def list_plugins(self, ctx: lightbulb.Context) -> None:
        try:
            loaded_plugins = self.bot.plugin_loader.get_loaded_plugins()

            if not loaded_plugins:
                embed = self.create_embed(
                    title="📦 Loaded Plugins",
                    description="No plugins are currently loaded.",
                    color=hikari.Color(0xFFAA00)
                )
            else:
                description = ""
                for plugin_name in loaded_plugins:
                    info = self.bot.plugin_loader.get_plugin_info(plugin_name)
                    if info:
                        description += f"**{plugin_name}** v{info.version}\n"
                        description += f"  └ {info.description}\n\n"
                    else:
                        description += f"**{plugin_name}**\n  └ No metadata available\n\n"

                embed = self.create_embed(
                    title="📦 Loaded Plugins",
                    description=description.strip(),
                    color=hikari.Color(0x7289DA)
                )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "plugins", True)

        except Exception as e:
            logger.error(f"Error in plugins command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to list plugins: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "plugins", False, str(e))

    @command(
        name="permission",
        description="Manage role permissions",
        permission_node="admin.permissions"
    )
    async def manage_permissions(self, ctx: lightbulb.Context) -> None:
        # Simple implementation for now - just show available permissions
        action = "list"  # Default to list for simplicity
        role = None
        permission = None
        try:
            if action == "list":
                if role:
                    # List permissions for a specific role
                    permissions = await self.bot.permission_manager.get_role_permissions(ctx.guild_id, role.id)
                    if permissions:
                        perm_list = "\n".join([f"• {perm}" for perm in permissions])
                        embed = self.create_embed(
                            title=f"🔑 Permissions for @{role.name}",
                            description=perm_list,
                            color=hikari.Color(0x7289DA)
                        )
                    else:
                        embed = self.create_embed(
                            title=f"🔑 Permissions for @{role.name}",
                            description="No permissions granted.",
                            color=hikari.Color(0xFFAA00)
                        )
                else:
                    # List all available permissions
                    all_perms = await self.bot.permission_manager.get_all_permissions()
                    if all_perms:
                        perm_list = "\n".join([f"• `{perm.node}` - {perm.description}" for perm in all_perms[:20]])
                        if len(all_perms) > 20:
                            perm_list += f"\n... and {len(all_perms) - 20} more"
                        embed = self.create_embed(
                            title="🔑 Available Permissions",
                            description=perm_list,
                            color=hikari.Color(0x7289DA)
                        )
                    else:
                        embed = self.create_embed(
                            title="🔑 Available Permissions",
                            description="No permissions found.",
                            color=hikari.Color(0xFFAA00)
                        )

            elif action in ["grant", "revoke"]:
                if not role or not permission:
                    embed = self.create_embed(
                        title="❌ Invalid Parameters",
                        description=f"Both role and permission are required for {action} action.",
                        color=hikari.Color(0xFF0000)
                    )
                else:
                    if action == "grant":
                        success = await self.bot.permission_manager.grant_permission(
                            ctx.guild_id, role.id, permission
                        )
                        action_text = "granted to"
                    else:
                        success = await self.bot.permission_manager.revoke_permission(
                            ctx.guild_id, role.id, permission
                        )
                        action_text = "revoked from"

                    if success:
                        embed = self.create_embed(
                            title="✅ Permission Updated",
                            description=f"Permission `{permission}` has been {action_text} @{role.name}",
                            color=hikari.Color(0x00FF00)
                        )
                    else:
                        embed = self.create_embed(
                            title="❌ Permission Update Failed",
                            description=f"Failed to {action} permission. Check if permission exists.",
                            color=hikari.Color(0xFF0000)
                        )
            else:
                embed = self.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: grant, revoke, list",
                    color=hikari.Color(0xFF0000)
                )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "permission", True)

        except Exception as e:
            logger.error(f"Error in permission command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "permission", False, str(e))

    @command(
        name="bot-info",
        description="Display bot information and statistics",
        aliases=["info"]
    )
    async def bot_info(self, ctx: lightbulb.Context) -> None:
        try:
            # Get bot info
            bot_user = self.bot.hikari_bot.get_me()
            guild_count = len(self.bot.hikari_bot.cache.get_guilds_view())

            # Get database health
            db_healthy = await self.bot.db.health_check()
            db_status = "✅ Connected" if db_healthy else "❌ Disconnected"

            # Get loaded plugins count
            plugin_count = len(self.bot.plugin_loader.get_loaded_plugins())

            embed = self.create_embed(
                title=f"🤖 {bot_user.username} Information",
                color=hikari.Color(0x7289DA)
            )

            embed.add_field("Guilds", str(guild_count), inline=True)
            embed.add_field("Plugins Loaded", str(plugin_count), inline=True)
            embed.add_field("Database", db_status, inline=True)

            embed.set_thumbnail(bot_user.display_avatar_url)

            if bot_user.created_at:
                embed.set_footer(f"Created on {bot_user.created_at.strftime('%B %d, %Y')}")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "bot-info", True)

        except Exception as e:
            logger.error(f"Error in bot-info command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to get bot information: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "bot-info", False, str(e))

    @command(
        name="demo-parse",
        description="Demo command showing advanced argument parsing",
        arguments=[
            CommandArgument("user", hikari.OptionType.USER, "A user to mention"),
            CommandArgument("channel", hikari.OptionType.CHANNEL, "A channel to reference", required=False),
            CommandArgument("role", hikari.OptionType.ROLE, "A role to check", required=False),
            CommandArgument("number", hikari.OptionType.INTEGER, "A number", required=False, default=42),
            CommandArgument("message", hikari.OptionType.STRING, "Additional message", required=False, default="Hello!")
        ]
    )
    async def demo_parse(self, ctx: lightbulb.Context, user, channel=None, role=None, number: int = 42, message: str = "Hello!") -> None:
        """Demonstrates the powerful argument parsing system."""
        try:
            embed = self.create_embed(
                title="🚀 Argument Parsing Demo",
                description="Here's what was parsed from your command:",
                color=hikari.Color(0x00FF00)
            )
            
            # User info
            if user:
                embed.add_field("👤 User", f"{user.mention} ({user.username})", inline=True)
            
            # Channel info  
            if channel:
                embed.add_field("📢 Channel", f"{channel.mention} ({channel.name})", inline=True)
            else:
                embed.add_field("📢 Channel", "None provided", inline=True)
                
            # Role info
            if role:
                embed.add_field("🎭 Role", f"{role.mention} ({role.name})", inline=True)
            else:
                embed.add_field("🎭 Role", "None provided", inline=True)
                
            # Number and message
            embed.add_field("🔢 Number", str(number), inline=True)
            embed.add_field("💬 Message", message, inline=True)
            
            # Usage examples
            examples = """
**Usage Examples:**
Slash: `/demo-parse @user #channel @role 123 Custom message here`
Prefix: `!demo-parse @user #channel @role 123 Custom message here`

**Also works with:**
- User IDs: `123456789`
- Channel names: `general`  
- Role names: `Admin`
- Usernames: `username`
            """.strip()
            
            embed.add_field("📖 Examples", examples, inline=False)
            
            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "demo-parse", True)
            
        except Exception as e:
            logger.error(f"Error in demo-parse command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Demo failed: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "demo-parse", False, str(e))