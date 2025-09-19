import logging

import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command
from bot.core.event_system import event_listener

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
        permission_node="admin.permissions",
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
                            color=hikari.Color(0x7289DA),
                        )
                    else:
                        embed = self.create_embed(
                            title=f"🔑 Permissions for @{role.name}",
                            description="No permissions granted.",
                            color=hikari.Color(0xFFAA00),
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
                            color=hikari.Color(0x7289DA),
                        )
                    else:
                        embed = self.create_embed(
                            title="🔑 Available Permissions",
                            description="No permissions found.",
                            color=hikari.Color(0xFFAA00),
                        )

            elif action in ["grant", "revoke"]:
                if not role or not permission:
                    embed = self.create_embed(
                        title="❌ Invalid Parameters",
                        description=f"Both role and permission are required for {action} action.",
                        color=hikari.Color(0xFF0000),
                    )
                else:
                    if action == "grant":
                        success = await self.bot.permission_manager.grant_permission(ctx.guild_id, role.id, permission)
                        action_text = "granted to"
                    else:
                        success = await self.bot.permission_manager.revoke_permission(ctx.guild_id, role.id, permission)
                        action_text = "revoked from"

                    if success:
                        embed = self.create_embed(
                            title="✅ Permission Updated",
                            description=f"Permission `{permission}` has been {action_text} @{role.name}",
                            color=hikari.Color(0x00FF00),
                        )
                    else:
                        embed = self.create_embed(
                            title="❌ Permission Update Failed",
                            description=f"Failed to {action} permission. Check if permission exists.",
                            color=hikari.Color(0xFF0000),
                        )
            else:
                embed = self.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: grant, revoke, list",
                    color=hikari.Color(0xFF0000),
                )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "permission", True)

        except Exception as e:
            logger.error(f"Error in permission command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "permission", False, str(e))

    @command(
        name="bot-info",
        description="Display bot information and statistics",
        aliases=["info"],
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
                color=hikari.Color(0x7289DA),
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
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "bot-info", False, str(e))

    @command(
        name="server-info",
        description="Display server information and statistics",
        aliases=["serverinfo", "guild-info"],
    )
    async def server_info(self, ctx: lightbulb.Context) -> None:
        try:
            guild = ctx.get_guild()
            if not guild:
                embed = self.create_embed(
                    title="❌ Error",
                    description="This command can only be used in a server.",
                    color=hikari.Color(0xFF0000),
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

            embed = self.create_embed(title=f"🏰 {guild.name}", color=hikari.Color(0x7289DA))

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
                    "DISCOVERABLE": "Server Discovery",
                }

                for feature in features:
                    if feature in feature_mapping:
                        feature_names.append(feature_mapping[feature])
                    elif len(feature_names) < 5:  # Limit features shown
                        feature_names.append(feature.replace("_", " ").title())

                if feature_names:
                    embed.add_field(
                        "✨ Features",
                        "\n".join([f"• {f}" for f in feature_names[:5]]),
                        inline=False,
                    )

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
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "server-info", False, str(e))

    @command(
        name="uptime",
        description="Display bot uptime and system information",
        aliases=["up", "status"],
    )
    async def uptime(self, ctx: lightbulb.Context) -> None:
        try:
            import time
            from datetime import datetime

            import psutil

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

            embed = self.create_embed(title="📊 Bot Status & Uptime", color=hikari.Color(0x00FF7F))

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
                color=hikari.Color(0x00FF7F),
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
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "uptime", False, str(e))

    @command(
        name="prefix",
        description="View or set the bot's prefix for this server",
        permission_node="admin.config",
        arguments=[
            CommandArgument(
                "new_prefix",
                hikari.OptionType.STRING,
                "New prefix to set (leave empty to view current prefix)",
                required=False,
            )
        ],
    )
    async def manage_prefix(self, ctx: lightbulb.Context, new_prefix: str = None) -> None:
        try:
            if not ctx.guild_id:
                embed = self.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if new_prefix is None:
                # Get current prefix
                current_prefix = await self.bot.get_guild_prefix(ctx.guild_id)
                embed = self.create_embed(
                    title="🔧 Current Server Prefix",
                    description=f"The current prefix for this server is: `{current_prefix}`",
                    color=hikari.Color(0x7289DA),
                )
                embed.add_field(
                    "Usage",
                    f"Use `{current_prefix}help` to see all commands\nUse `/prefix <new_prefix>` to change the prefix",
                    inline=False,
                )
            else:
                # Validate new prefix
                if len(new_prefix) > 5:
                    embed = self.create_embed(
                        title="❌ Invalid Prefix",
                        description="Prefix must be 5 characters or less.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                if len(new_prefix.strip()) == 0:
                    embed = self.create_embed(
                        title="❌ Invalid Prefix",
                        description="Prefix cannot be empty or only whitespace.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                # Check for problematic characters
                problematic_chars = ['"', "'", "`", "\n", "\r", "\t"]
                if any(char in new_prefix for char in problematic_chars):
                    embed = self.create_embed(
                        title="❌ Invalid Prefix",
                        description="Prefix cannot contain quotes, backticks, or whitespace characters.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                # Update prefix in database
                async with self.bot.db.session() as session:
                    from bot.database.models import Guild
                    from sqlalchemy import select

                    # Get or create guild
                    result = await session.execute(select(Guild).where(Guild.id == ctx.guild_id))
                    guild = result.scalar_one_or_none()

                    if not guild:
                        # Create new guild entry
                        guild_obj = ctx.get_guild()
                        guild = Guild(
                            id=ctx.guild_id,
                            name=guild_obj.name if guild_obj else "Unknown",
                            prefix=new_prefix,
                        )
                        session.add(guild)
                    else:
                        # Update existing guild
                        guild.prefix = new_prefix

                    await session.commit()

                embed = self.create_embed(
                    title="✅ Prefix Updated",
                    description=f"Server prefix has been changed to: `{new_prefix}`",
                    color=hikari.Color(0x00FF00),
                )
                embed.add_field(
                    "Usage",
                    f"Use `{new_prefix}help` to see all commands",
                    inline=False,
                )
                embed.add_field("Changed by", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "prefix", True)

        except Exception as e:
            logger.error(f"Error in prefix command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to manage prefix: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "prefix", False, str(e))

    @command(
        name="autorole",
        description="Configure roles automatically assigned to new members",
        permission_node="admin.config",
        arguments=[
            CommandArgument(
                "action",
                hikari.OptionType.STRING,
                "Action: add, remove, list, or clear",
            ),
            CommandArgument(
                "role",
                hikari.OptionType.ROLE,
                "Role to add/remove (not needed for list/clear)",
                required=False,
            ),
        ],
    )
    async def autorole(self, ctx: lightbulb.Context, action: str, role: hikari.Role = None) -> None:
        try:
            if not ctx.guild_id:
                embed = self.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            action = action.lower().strip()

            # Get current autoroles
            current_autoroles = await self.get_setting(ctx.guild_id, "autoroles", [])

            if action == "list":
                if not current_autoroles:
                    embed = self.create_embed(
                        title="📋 Auto Roles",
                        description="No auto roles are currently configured.",
                        color=hikari.Color(0x7289DA),
                    )
                else:
                    role_mentions = []
                    for role_id in current_autoroles:
                        try:
                            role_obj = ctx.get_guild().get_role(role_id)
                            if role_obj:
                                role_mentions.append(role_obj.mention)
                        except Exception:
                            # Role might have been deleted
                            pass

                    if role_mentions:
                        embed = self.create_embed(
                            title="📋 Auto Roles",
                            description=f"New members automatically receive:\n" + "\n".join([f"• {role}" for role in role_mentions]),
                            color=hikari.Color(0x7289DA),
                        )
                    else:
                        embed = self.create_embed(
                            title="📋 Auto Roles",
                            description="No valid auto roles found (they may have been deleted).",
                            color=hikari.Color(0xFFAA00),
                        )

            elif action == "clear":
                await self.set_setting(ctx.guild_id, "autoroles", [])
                embed = self.create_embed(
                    title="✅ Auto Roles Cleared",
                    description="All auto roles have been removed.",
                    color=hikari.Color(0x00FF00),
                )

            elif action in ["add", "remove"]:
                if not role:
                    embed = self.create_embed(
                        title="❌ Missing Role",
                        description=f"Please specify a role to {action}.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                # Check if bot can assign this role
                bot_member = ctx.get_guild().get_member(ctx.client.get_me().id)
                if not bot_member:
                    embed = self.create_embed(
                        title="❌ Bot Permission Error",
                        description="Cannot verify bot permissions.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                bot_top_role = max(bot_member.role_ids) if bot_member.role_ids else ctx.guild_id
                bot_role = ctx.get_guild().get_role(bot_top_role) if bot_top_role != ctx.guild_id else None

                if bot_role and role.position >= bot_role.position:
                    embed = self.create_embed(
                        title="❌ Role Hierarchy Error",
                        description=f"I cannot assign {role.mention} because it's higher than or equal to my highest role.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                if action == "add":
                    if role.id in current_autoroles:
                        embed = self.create_embed(
                            title="❌ Already Configured",
                            description=f"{role.mention} is already an auto role.",
                            color=hikari.Color(0xFF0000),
                        )
                    else:
                        current_autoroles.append(role.id)
                        await self.set_setting(ctx.guild_id, "autoroles", current_autoroles)
                        embed = self.create_embed(
                            title="✅ Auto Role Added",
                            description=f"{role.mention} will now be automatically assigned to new members.",
                            color=hikari.Color(0x00FF00),
                        )

                elif action == "remove":
                    if role.id not in current_autoroles:
                        embed = self.create_embed(
                            title="❌ Not Configured",
                            description=f"{role.mention} is not an auto role.",
                            color=hikari.Color(0xFF0000),
                        )
                    else:
                        current_autoroles.remove(role.id)
                        await self.set_setting(ctx.guild_id, "autoroles", current_autoroles)
                        embed = self.create_embed(
                            title="✅ Auto Role Removed",
                            description=f"{role.mention} will no longer be automatically assigned to new members.",
                            color=hikari.Color(0x00FF00),
                        )

            else:
                embed = self.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: `add`, `remove`, `list`, `clear`",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "autorole", True)

        except Exception as e:
            logger.error(f"Error in autorole command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to manage auto roles: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "autorole", False, str(e))

    @event_listener("member_join")
    async def on_member_join(self, member: hikari.Member) -> None:
        """Handle new member joins and assign auto roles."""
        try:
            # Get autoroles for this guild
            autoroles = await self.get_setting(member.guild_id, "autoroles", [])

            if not autoroles:
                return  # No autoroles configured

            guild = self.bot.hikari_bot.cache.get_guild(member.guild_id)
            if not guild:
                return

            # Assign each autorole
            roles_assigned = []
            for role_id in autoroles:
                try:
                    role = guild.get_role(role_id)
                    if role:
                        await member.add_role(role, reason="Auto role assignment")
                        roles_assigned.append(role.name)
                        logger.info(f"Assigned auto role {role.name} to {member.username} in {guild.name}")
                except Exception as e:
                    logger.error(f"Failed to assign auto role {role_id} to {member.username}: {e}")

            if roles_assigned:
                logger.info(f"Assigned {len(roles_assigned)} auto roles to {member.username} in {guild.name}")

        except Exception as e:
            logger.error(f"Error in auto role assignment for {member.username}: {e}")
