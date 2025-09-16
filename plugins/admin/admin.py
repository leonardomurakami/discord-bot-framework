import logging
import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

# Plugin metadata for the loader
PLUGIN_METADATA = {
    "name": "Admin",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Administrative commands for bot management including permissions, server info, and uptime monitoring",
    "permissions": ["admin.config", "admin.plugins", "admin.permissions"],
}

logger = logging.getLogger(__name__)


class AdminPlugin(BasePlugin):
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
        name="server-info",
        description="Display server information and statistics",
        aliases=["serverinfo", "guild-info"]
    )
    async def server_info(self, ctx: lightbulb.Context) -> None:
        try:
            guild = ctx.get_guild()
            if not guild:
                embed = self.create_embed(
                    title="❌ Error",
                    description="This command can only be used in a server.",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Get server statistics
            member_count = guild.member_count or 0
            channel_count = len(guild.get_channels())
            role_count = len(guild.get_roles())
            emoji_count = len(guild.get_emojis())

            # Count channel types
            text_channels = len([c for c in guild.get_channels().values() if c.type == hikari.ChannelType.GUILD_TEXT])
            voice_channels = len([c for c in guild.get_channels().values() if c.type == hikari.ChannelType.GUILD_VOICE])
            category_channels = len([c for c in guild.get_channels().values() if c.type == hikari.ChannelType.GUILD_CATEGORY])

            embed = self.create_embed(
                title=f"🏰 {guild.name}",
                color=hikari.Color(0x7289DA)
            )

            # Basic info
            embed.add_field("Server ID", str(guild.id), inline=True)
            embed.add_field("Owner", f"<@{guild.owner_id}>", inline=True)
            embed.add_field("Created", f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)

            # Statistics
            embed.add_field("👥 Members", str(member_count), inline=True)
            embed.add_field("📺 Channels", f"{channel_count} total", inline=True)
            embed.add_field("🎭 Roles", str(role_count), inline=True)

            # Channel breakdown
            channel_breakdown = f"💬 Text: {text_channels}\n🔊 Voice: {voice_channels}\n📁 Categories: {category_channels}"
            embed.add_field("Channel Breakdown", channel_breakdown, inline=True)

            embed.add_field("😀 Emojis", str(emoji_count), inline=True)

            # Features
            features = guild.features
            if features:
                feature_names = []
                feature_mapping = {
                    "COMMUNITY": "Community Server",
                    "VERIFIED": "Verified",
                    "PARTNERED": "Partnered",
                    "ANIMATED_ICON": "Animated Icon",
                    "BANNER": "Server Banner",
                    "VANITY_URL": "Custom Invite URL",
                    "INVITE_SPLASH": "Invite Splash",
                    "NEWS": "News Channels",
                    "DISCOVERABLE": "Server Discovery"
                }

                for feature in features:
                    if feature in feature_mapping:
                        feature_names.append(feature_mapping[feature])
                    elif len(feature_names) < 5:  # Limit features shown
                        feature_names.append(feature.replace("_", " ").title())

                if feature_names:
                    embed.add_field("✨ Features", "\n".join([f"• {f}" for f in feature_names[:5]]), inline=False)

            # Set server icon as thumbnail
            icon_url = guild.make_icon_url()
            if icon_url:
                embed.set_thumbnail(icon_url)

            # Set server banner if available
            banner_url = guild.make_banner_url()
            if banner_url:
                embed.set_image(banner_url)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "server-info", True)

        except Exception as e:
            logger.error(f"Error in server-info command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to get server information: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "server-info", False, str(e))

    @command(
        name="uptime",
        description="Display bot uptime and system information",
        aliases=["up", "status"]
    )
    async def uptime(self, ctx: lightbulb.Context) -> None:
        try:
            import psutil
            import time
            from datetime import datetime

            # Get bot start time (approximation using process start time)
            process = psutil.Process()
            process_start_time = process.create_time()
            bot_start_time = datetime.fromtimestamp(process_start_time)

            # Calculate uptime
            current_time = datetime.now()
            uptime_delta = current_time - bot_start_time

            # Format uptime
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            uptime_str = []
            if days > 0:
                uptime_str.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                uptime_str.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                uptime_str.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if seconds > 0 or not uptime_str:
                uptime_str.append(f"{seconds} second{'s' if seconds != 1 else ''}")

            formatted_uptime = ", ".join(uptime_str)

            embed = self.create_embed(
                title="📊 Bot Status & Uptime",
                color=hikari.Color(0x00FF7F)
            )

            embed.add_field("⏰ Uptime", formatted_uptime, inline=True)
            embed.add_field("🚀 Started", f"<t:{int(process_start_time)}:R>", inline=True)
            embed.add_field("📅 Current Time", f"<t:{int(current_time.timestamp())}:f>", inline=True)

            # System information
            try:
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                embed.add_field("💾 Memory Usage", f"{memory_mb:.1f} MB", inline=True)
                embed.add_field("⚡ CPU Usage", f"{cpu_percent:.1f}%", inline=True)

                # System uptime
                system_uptime = time.time() - psutil.boot_time()
                system_days = int(system_uptime // 86400)
                system_hours = int((system_uptime % 86400) // 3600)
                system_uptime_str = f"{system_days}d {system_hours}h"
                embed.add_field("🖥️ System Uptime", system_uptime_str, inline=True)

            except Exception:
                # If system info fails, just show basic uptime
                pass

            # Bot info
            guild_count = len(self.bot.hikari_bot.cache.get_guilds_view())
            embed.add_field("🏰 Servers", str(guild_count), inline=True)

            # Ping/Latency
            try:
                latency = self.bot.hikari_bot.heartbeat_latency * 1000
                embed.add_field("📡 Latency", f"{latency:.1f}ms", inline=True)
            except Exception:
                pass

            embed.set_footer(f"Process ID: {process.pid}")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "uptime", True)

        except ImportError:
            # Fallback if psutil is not available
            embed = self.create_embed(
                title="📊 Bot Status",
                description="Bot is online and responding!",
                color=hikari.Color(0x00FF7F)
            )

            guild_count = len(self.bot.hikari_bot.cache.get_guilds_view())
            embed.add_field("🏰 Servers", str(guild_count), inline=True)

            try:
                latency = self.bot.hikari_bot.heartbeat_latency * 1000
                embed.add_field("📡 Latency", f"{latency:.1f}ms", inline=True)
            except Exception:
                pass

            embed.set_footer("Install 'psutil' for detailed system information")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "uptime", True)

        except Exception as e:
            logger.error(f"Error in uptime command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to get uptime information: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "uptime", False, str(e))
