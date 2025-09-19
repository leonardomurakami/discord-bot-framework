import logging
from datetime import datetime, timedelta

import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command

# Plugin metadata for the loader
PLUGIN_METADATA = {
    "name": "Moderation",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Moderation commands for server management including kick, ban, timeout, slowmode, and message purging",
    "permissions": [
        "moderation.kick",
        "moderation.ban",
        "moderation.mute",
        "moderation.warn",
        "moderation.purge",
        "moderation.timeout",
        "moderation.slowmode",
    ],
}

logger = logging.getLogger(__name__)


class ModerationPlugin(BasePlugin):
    @command(
        name="kick",
        description="Kick a member from the server",
        permission_node="moderation.kick",
    )
    async def kick_member(self, ctx: lightbulb.Context) -> None:
        # Get member and reason from options or args
        member = None
        reason = "No reason provided"

        if hasattr(ctx, "options"):
            member = getattr(ctx.options, "member", None)
            reason = getattr(ctx.options, "reason", "No reason provided")
        elif hasattr(ctx, "args") and ctx.args:
            # For prefix commands, expect member mention/ID as first arg
            if len(ctx.args) >= 1:
                try:
                    member_id = int(ctx.args[0].strip("<@!>"))
                    member = ctx.get_guild().get_member(member_id)
                except (ValueError, AttributeError):
                    pass
            if len(ctx.args) >= 2:
                reason = " ".join(ctx.args[1:])

        if not member:
            embed = self.create_embed(
                title="❌ Invalid Member",
                description="Please specify a valid member to kick.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            return
        try:
            if member.id == ctx.author.id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot kick yourself!",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.client.get_me().id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot kick myself!",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Try to send DM before kicking
            try:
                dm_channel = await member.fetch_dm_channel()
                embed_dm = self.create_embed(
                    title="🦵 You have been kicked",
                    description=f"You have been kicked from **{ctx.get_guild().name}**",
                    color=hikari.Color(0xFF6600),
                )
                embed_dm.add_field("Reason", reason, inline=False)
                embed_dm.add_field("Moderator", f"{ctx.author.mention}", inline=True)
                await dm_channel.send(embed=embed_dm)
            except Exception:
                pass  # DM failed, continue with kick

            await ctx.get_guild().kick(member, reason=f"{reason} (by {ctx.author})")

            embed = self.create_embed(
                title="✅ Member Kicked",
                description=f"{member.mention} has been kicked from the server.",
                color=hikari.Color(0x00FF00),
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "kick", True)

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to kick this member. They might have higher roles than me.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "kick", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in kick command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to kick member: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "kick", False, str(e))

    @command(
        name="ban",
        description="Ban a member from the server",
        permission_node="moderation.ban",
    )
    async def ban_member(self, ctx: lightbulb.Context) -> None:
        # Get user, delete_days, and reason from options or args
        user = None
        delete_days = 1
        reason = "No reason provided"

        if hasattr(ctx, "options"):
            user = getattr(ctx.options, "user", None)
            delete_days = getattr(ctx.options, "delete_days", 1)
            reason = getattr(ctx.options, "reason", "No reason provided")
        elif hasattr(ctx, "args") and ctx.args:
            # For prefix commands, expect user mention/ID as first arg
            if len(ctx.args) >= 1:
                try:
                    user_id = int(ctx.args[0].strip("<@!>"))
                    user = await self.bot.hikari_bot.rest.fetch_user(user_id)
                except (ValueError, AttributeError, hikari.NotFoundError):
                    pass
            if len(ctx.args) >= 2:
                try:
                    delete_days = int(ctx.args[1])
                except ValueError:
                    pass
            if len(ctx.args) >= 3:
                reason = " ".join(ctx.args[2:])

        if not user:
            embed = self.create_embed(
                title="❌ Invalid User",
                description="Please specify a valid user to ban.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            return
        try:
            if user.id == ctx.author.id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot ban yourself!",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if user.id == ctx.client.get_me().id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot ban myself!",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Try to send DM before banning (if user is a member)
            try:
                member = ctx.get_guild().get_member(user.id)
                if member:
                    dm_channel = await user.fetch_dm_channel()
                    embed_dm = self.create_embed(
                        title="🔨 You have been banned",
                        description=f"You have been banned from **{ctx.get_guild().name}**",
                        color=hikari.Color(0xFF0000),
                    )
                    embed_dm.add_field("Reason", reason, inline=False)
                    embed_dm.add_field("Moderator", f"{ctx.author.mention}", inline=True)
                    await dm_channel.send(embed=embed_dm)
            except Exception:
                pass  # DM failed, continue with ban

            await ctx.get_guild().ban(
                user,
                delete_message_days=delete_days,
                reason=f"{reason} (by {ctx.author})",
            )

            embed = self.create_embed(
                title="✅ User Banned",
                description=f"{user.mention} has been banned from the server.",
                color=hikari.Color(0x00FF00),
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Messages Deleted", f"{delete_days} days", inline=True)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "ban", True)

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to ban this user. They might have higher roles than me.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "ban", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in ban command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to ban user: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "ban", False, str(e))

    @command(
        name="timeout",
        description="Timeout a member for a specified duration",
        permission_node="moderation.timeout",
    )
    async def timeout_member(self, ctx: lightbulb.Context) -> None:
        # Get member, duration, and reason from options or args
        member = None
        duration = 0
        reason = "No reason provided"

        if hasattr(ctx, "options"):
            member = getattr(ctx.options, "member", None)
            duration = getattr(ctx.options, "duration", 0)
            reason = getattr(ctx.options, "reason", "No reason provided")
        elif hasattr(ctx, "args") and len(ctx.args) >= 2:
            # For prefix commands, expect member mention/ID and duration
            try:
                member_id = int(ctx.args[0].strip("<@!>"))
                member = ctx.get_guild().get_member(member_id)
                duration = int(ctx.args[1])
            except (ValueError, AttributeError):
                pass
            if len(ctx.args) >= 3:
                reason = " ".join(ctx.args[2:])

        if not member or duration <= 0:
            embed = self.create_embed(
                title="❌ Invalid Parameters",
                description="Please specify a valid member and duration in minutes.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            return
        try:
            if member.id == ctx.author.id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot timeout yourself!",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.client.get_me().id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot timeout myself!",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Calculate timeout end time
            timeout_until = datetime.now() + timedelta(minutes=duration)

            await member.edit(
                communication_disabled_until=timeout_until,
                reason=f"{reason} (by {ctx.author})",
            )

            # Format duration
            if duration < 60:
                duration_str = f"{duration} minute(s)"
            else:
                hours = duration // 60
                minutes = duration % 60
                duration_str = f"{hours} hour(s)"
                if minutes > 0:
                    duration_str += f" and {minutes} minute(s)"

            embed = self.create_embed(
                title="✅ Member Timed Out",
                description=f"{member.mention} has been timed out for {duration_str}.",
                color=hikari.Color(0x00FF00),
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Duration", duration_str, inline=True)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "timeout", True)

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to timeout this member. They might have higher roles than me.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "timeout", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in timeout command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to timeout member: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "timeout", False, str(e))

    @command(
        name="purge",
        description="Delete multiple messages from a channel",
        aliases=["clear"],
        permission_node="moderation.purge",
        arguments=[
            CommandArgument(
                "amount",
                hikari.OptionType.INTEGER,
                "Number of messages to delete (1-100)",
            ),
            CommandArgument(
                "user",
                hikari.OptionType.USER,
                "Only delete messages from this user",
                required=False,
            ),
        ],
    )
    async def purge_messages(self, ctx: lightbulb.Context, amount: int, user=None) -> None:
        if amount <= 0 or amount > 100:
            embed = self.create_embed(
                title="❌ Invalid Amount",
                description="Please specify a number between 1 and 100 messages to delete.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            return
        try:
            channel = ctx.get_channel()

            # Defer response since this might take a while
            await ctx.defer()

            if user:
                # Get messages from specific user
                messages = []
                async for message in channel.fetch_history(limit=500):
                    if message.author.id == user.id:
                        messages.append(message)
                        if len(messages) >= amount:
                            break

                deleted_count = len(messages)
                if messages:
                    await channel.delete_messages(messages)

                embed = self.create_embed(
                    title="✅ Messages Purged",
                    description=f"Deleted {deleted_count} message(s) from {user.mention}.",
                    color=hikari.Color(0x00FF00),
                )
            else:
                # Delete last N messages
                messages = []
                async for message in channel.fetch_history(limit=amount):
                    messages.append(message)

                if messages:
                    await channel.delete_messages(messages)

                embed = self.create_embed(
                    title="✅ Messages Purged",
                    description=f"Deleted {len(messages)} message(s) from this channel.",
                    color=hikari.Color(0x00FF00),
                )

            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "purge", True)

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages in this channel.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "purge", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in purge command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to purge messages: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "purge", False, str(e))

    @command(
        name="unban",
        description="Unban a user from the server",
        permission_node="moderation.ban",
        arguments=[
            CommandArgument("user_id", hikari.OptionType.STRING, "User ID to unban"),
            CommandArgument(
                "reason",
                hikari.OptionType.STRING,
                "Reason for unbanning",
                required=False,
                default="No reason provided",
            ),
        ],
    )
    async def unban_user(self, ctx: lightbulb.Context, user_id: str, reason: str = "No reason provided") -> None:
        try:
            # Try to convert user_id to int
            try:
                user_id_int = int(user_id.strip("<@!>"))
            except ValueError:
                embed = self.create_embed(
                    title="❌ Invalid User ID",
                    description="Please provide a valid user ID or mention.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Check if user is actually banned
            try:
                banned_users = []
                async for ban in ctx.get_guild().fetch_bans():
                    banned_users.append(ban.user.id)
                    if ban.user.id == user_id_int:
                        banned_user = ban.user
                        break
                else:
                    embed = self.create_embed(
                        title="❌ User Not Banned",
                        description="This user is not currently banned from the server.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

            except hikari.ForbiddenError:
                embed = self.create_embed(
                    title="❌ Permission Error",
                    description="I don't have permission to view the ban list.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Unban the user
            await ctx.get_guild().unban(user_id_int, reason=f"{reason} (by {ctx.author})")

            embed = self.create_embed(
                title="✅ User Unbanned",
                description=f"{banned_user.mention} ({banned_user.username}) has been unbanned.",
                color=hikari.Color(0x00FF00),
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Moderator", ctx.author.mention, inline=True)
            embed.add_field("User ID", str(user_id_int), inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "unban", True)

        except hikari.NotFoundError:
            embed = self.create_embed(
                title="❌ User Not Found",
                description="User not found in the ban list or invalid user ID.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "unban", False, "User not found")

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to unban users.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "unban", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in unban command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to unban user: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "unban", False, str(e))

    @command(
        name="slowmode",
        description="Set channel slowmode (rate limit)",
        aliases=["slow"],
        permission_node="moderation.slowmode",
        arguments=[
            CommandArgument(
                "seconds",
                hikari.OptionType.INTEGER,
                "Slowmode in seconds (0-21600, 0 to disable)",
                required=False,
                default=0,
            ),
            CommandArgument(
                "channel",
                hikari.OptionType.CHANNEL,
                "Channel to apply slowmode to (default: current channel)",
                required=False,
            ),
        ],
    )
    async def slowmode(self, ctx: lightbulb.Context, seconds: int = 0, channel=None) -> None:
        try:
            # Validate seconds
            if seconds < 0 or seconds > 21600:  # Discord's limit is 6 hours (21600 seconds)
                embed = self.create_embed(
                    title="❌ Invalid Duration",
                    description="Slowmode must be between 0 and 21600 seconds (6 hours).",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Use current channel if none specified
            target_channel = channel or ctx.get_channel()

            # Check if it's a text channel
            if target_channel.type not in [
                hikari.ChannelType.GUILD_TEXT,
                hikari.ChannelType.GUILD_NEWS,
            ]:
                embed = self.create_embed(
                    title="❌ Invalid Channel",
                    description="Slowmode can only be applied to text channels.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Apply slowmode
            await target_channel.edit(rate_limit_per_user=seconds)

            # Format duration for display
            if seconds == 0:
                duration_text = "disabled"
                title_emoji = "🚫"
                title_text = "Slowmode Disabled"
            else:
                if seconds < 60:
                    duration_text = f"{seconds} second(s)"
                elif seconds < 3600:
                    minutes = seconds // 60
                    remaining_seconds = seconds % 60
                    if remaining_seconds == 0:
                        duration_text = f"{minutes} minute(s)"
                    else:
                        duration_text = f"{minutes} minute(s) and {remaining_seconds} second(s)"
                else:
                    hours = seconds // 3600
                    remaining_minutes = (seconds % 3600) // 60
                    if remaining_minutes == 0:
                        duration_text = f"{hours} hour(s)"
                    else:
                        duration_text = f"{hours} hour(s) and {remaining_minutes} minute(s)"

                title_emoji = "🐌"
                title_text = "Slowmode Enabled"

            embed = self.create_embed(
                title=f"{title_emoji} {title_text}",
                description=f"Slowmode has been set to **{duration_text}** in {target_channel.mention}.",
                color=(hikari.Color(0x00FF00) if seconds == 0 else hikari.Color(0xFFAA00)),
            )

            embed.add_field("Channel", target_channel.mention, inline=True)
            embed.add_field("Duration", duration_text, inline=True)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            if seconds > 0:
                embed.set_footer("Users must wait between sending messages in this channel")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "slowmode", True)

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "slowmode", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in slowmode command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to set slowmode: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "slowmode", False, str(e))

    @command(
        name="warn",
        description="Issue a warning to a member",
        permission_node="moderation.warn",
        arguments=[
            CommandArgument(
                "member",
                hikari.OptionType.USER,
                "Member to warn",
            ),
            CommandArgument(
                "reason",
                hikari.OptionType.STRING,
                "Reason for the warning",
                required=False,
                default="No reason provided",
            ),
        ],
    )
    async def warn_member(self, ctx: lightbulb.Context, member: hikari.User, reason: str = "No reason provided") -> None:
        try:
            if not ctx.guild_id:
                embed = self.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.author.id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot warn yourself!",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.client.get_me().id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot warn myself!",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Get current warnings
            current_warnings = await self.get_setting(ctx.guild_id, "user_warnings", {})
            user_warnings = current_warnings.get(str(member.id), [])

            # Add new warning
            from datetime import datetime
            warning_data = {
                "reason": reason,
                "moderator": ctx.author.id,
                "timestamp": int(datetime.now().timestamp()),
                "id": len(user_warnings) + 1
            }
            user_warnings.append(warning_data)
            current_warnings[str(member.id)] = user_warnings

            # Save warnings
            await self.set_setting(ctx.guild_id, "user_warnings", current_warnings)

            # Try to send DM to warned user
            try:
                dm_channel = await member.fetch_dm_channel()
                embed_dm = self.create_embed(
                    title="⚠️ You have been warned",
                    description=f"You have been warned in **{ctx.get_guild().name}**",
                    color=hikari.Color(0xFFAA00),
                )
                embed_dm.add_field("Reason", reason, inline=False)
                embed_dm.add_field("Moderator", f"{ctx.author.mention}", inline=True)
                embed_dm.add_field("Warning Count", f"{len(user_warnings)}", inline=True)
                await dm_channel.send(embed=embed_dm)
            except Exception:
                pass  # DM failed, continue with warning

            embed = self.create_embed(
                title="✅ Member Warned",
                description=f"{member.mention} has been warned.",
                color=hikari.Color(0xFFAA00),
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Moderator", ctx.author.mention, inline=True)
            embed.add_field("Total Warnings", f"{len(user_warnings)}", inline=True)
            embed.add_field("Warning ID", f"#{warning_data['id']}", inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "warn", True)

        except Exception as e:
            logger.error(f"Error in warn command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to warn member: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "warn", False, str(e))

    @command(
        name="warnings",
        description="View warnings for a member",
        aliases=["warns"],
        permission_node="moderation.warn",
        arguments=[
            CommandArgument(
                "member",
                hikari.OptionType.USER,
                "Member to view warnings for",
                required=False,
            ),
        ],
    )
    async def view_warnings(self, ctx: lightbulb.Context, member: hikari.User = None) -> None:
        try:
            if not ctx.guild_id:
                embed = self.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            target_member = member or ctx.author

            # Get warnings
            current_warnings = await self.get_setting(ctx.guild_id, "user_warnings", {})
            user_warnings = current_warnings.get(str(target_member.id), [])

            if not user_warnings:
                embed = self.create_embed(
                    title="📋 No Warnings",
                    description=f"{target_member.mention} has no warnings.",
                    color=hikari.Color(0x00FF00),
                )
            else:
                embed = self.create_embed(
                    title=f"⚠️ Warnings for {target_member.display_name}",
                    description=f"Total warnings: **{len(user_warnings)}**",
                    color=hikari.Color(0xFFAA00),
                )

                # Show recent warnings (max 5)
                recent_warnings = user_warnings[-5:]
                for warning in recent_warnings:
                    moderator_id = warning.get("moderator", "Unknown")
                    timestamp = warning.get("timestamp", 0)
                    reason = warning.get("reason", "No reason provided")
                    warning_id = warning.get("id", "Unknown")

                    embed.add_field(
                        f"Warning #{warning_id}",
                        f"**Reason:** {reason}\n**Moderator:** <@{moderator_id}>\n**Date:** <t:{timestamp}:f>",
                        inline=False
                    )

                if len(user_warnings) > 5:
                    embed.set_footer(f"Showing 5 most recent warnings out of {len(user_warnings)} total")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "warnings", True)

        except Exception as e:
            logger.error(f"Error in warnings command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to retrieve warnings: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "warnings", False, str(e))

    @command(
        name="modnote",
        description="Add or view private moderator notes on users",
        permission_node="moderation.warn",
        arguments=[
            CommandArgument(
                "action",
                hikari.OptionType.STRING,
                "Action: add, view, or clear",
            ),
            CommandArgument(
                "member",
                hikari.OptionType.USER,
                "Member to add note for",
            ),
            CommandArgument(
                "note",
                hikari.OptionType.STRING,
                "Note content (required for 'add' action)",
                required=False,
            ),
        ],
    )
    async def mod_note(self, ctx: lightbulb.Context, action: str, member: hikari.User, note: str = None) -> None:
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

            # Get current notes
            current_notes = await self.get_setting(ctx.guild_id, "user_notes", {})
            user_notes = current_notes.get(str(member.id), [])

            if action == "add":
                if not note:
                    embed = self.create_embed(
                        title="❌ Missing Note",
                        description="Please provide a note to add.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                # Add new note
                from datetime import datetime
                note_data = {
                    "note": note,
                    "moderator": ctx.author.id,
                    "timestamp": int(datetime.now().timestamp()),
                    "id": len(user_notes) + 1
                }
                user_notes.append(note_data)
                current_notes[str(member.id)] = user_notes

                # Save notes
                await self.set_setting(ctx.guild_id, "user_notes", current_notes)

                embed = self.create_embed(
                    title="✅ Note Added",
                    description=f"Added moderator note for {member.mention}",
                    color=hikari.Color(0x00FF00),
                )
                embed.add_field("Note", note, inline=False)
                embed.add_field("Total Notes", f"{len(user_notes)}", inline=True)

            elif action == "view":
                if not user_notes:
                    embed = self.create_embed(
                        title="📋 No Notes",
                        description=f"No moderator notes found for {member.mention}.",
                        color=hikari.Color(0x7289DA),
                    )
                else:
                    embed = self.create_embed(
                        title=f"📝 Moderator Notes for {member.display_name}",
                        description=f"Total notes: **{len(user_notes)}**",
                        color=hikari.Color(0x7289DA),
                    )

                    # Show recent notes (max 5)
                    recent_notes = user_notes[-5:]
                    for note_data in recent_notes:
                        moderator_id = note_data.get("moderator", "Unknown")
                        timestamp = note_data.get("timestamp", 0)
                        note_content = note_data.get("note", "No content")
                        note_id = note_data.get("id", "Unknown")

                        embed.add_field(
                            f"Note #{note_id}",
                            f"**Content:** {note_content}\n**By:** <@{moderator_id}>\n**Date:** <t:{timestamp}:f>",
                            inline=False
                        )

                    if len(user_notes) > 5:
                        embed.set_footer(f"Showing 5 most recent notes out of {len(user_notes)} total")

            elif action == "clear":
                if user_notes:
                    current_notes[str(member.id)] = []
                    await self.set_setting(ctx.guild_id, "user_notes", current_notes)

                    embed = self.create_embed(
                        title="✅ Notes Cleared",
                        description=f"Cleared all moderator notes for {member.mention}",
                        color=hikari.Color(0x00FF00),
                    )
                    embed.add_field("Notes Removed", f"{len(user_notes)}", inline=True)
                else:
                    embed = self.create_embed(
                        title="📋 No Notes",
                        description=f"No moderator notes found for {member.mention}.",
                        color=hikari.Color(0x7289DA),
                    )

            else:
                embed = self.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: `add`, `view`, `clear`",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "modnote", True)

        except Exception as e:
            logger.error(f"Error in modnote command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to manage moderator note: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "modnote", False, str(e))

    @command(
        name="lockdown",
        description="Lock or unlock a channel temporarily",
        aliases=["lock", "unlock"],
        permission_node="moderation.slowmode",
        arguments=[
            CommandArgument(
                "action",
                hikari.OptionType.STRING,
                "Action: lock or unlock",
            ),
            CommandArgument(
                "channel",
                hikari.OptionType.CHANNEL,
                "Channel to lock/unlock (default: current channel)",
                required=False,
            ),
            CommandArgument(
                "reason",
                hikari.OptionType.STRING,
                "Reason for lockdown",
                required=False,
                default="No reason provided",
            ),
        ],
    )
    async def lockdown_channel(self, ctx: lightbulb.Context, action: str, channel=None, reason: str = "No reason provided") -> None:
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
            target_channel = channel or ctx.get_channel()

            if action not in ["lock", "unlock"]:
                embed = self.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: `lock`, `unlock`",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Check if it's a text channel
            if target_channel.type not in [
                hikari.ChannelType.GUILD_TEXT,
                hikari.ChannelType.GUILD_NEWS,
            ]:
                embed = self.create_embed(
                    title="❌ Invalid Channel",
                    description="Lockdown can only be applied to text channels.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            guild = ctx.get_guild()
            everyone_role = guild.get_role(ctx.guild_id)  # @everyone role has same ID as guild

            if not everyone_role:
                embed = self.create_embed(
                    title="❌ Permission Error",
                    description="Could not find @everyone role.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if action == "lock":
                # Remove send message permission from @everyone
                await target_channel.edit_overwrite(
                    everyone_role,
                    deny=hikari.Permissions.SEND_MESSAGES,
                    reason=f"Channel lockdown: {reason} (by {ctx.author})"
                )

                # Store lockdown info
                lockdown_data = await self.get_setting(ctx.guild_id, "lockdowns", {})
                lockdown_data[str(target_channel.id)] = {
                    "moderator": ctx.author.id,
                    "reason": reason,
                    "timestamp": int(datetime.now().timestamp())
                }
                await self.set_setting(ctx.guild_id, "lockdowns", lockdown_data)

                embed = self.create_embed(
                    title="🔒 Channel Locked",
                    description=f"{target_channel.mention} has been locked down.",
                    color=hikari.Color(0xFF0000),
                )
                embed.add_field("Reason", reason, inline=False)
                embed.add_field("Moderator", ctx.author.mention, inline=True)

            else:  # unlock
                # Restore send message permission to @everyone
                await target_channel.edit_overwrite(
                    everyone_role,
                    allow=hikari.Permissions.SEND_MESSAGES,
                    reason=f"Channel unlock: {reason} (by {ctx.author})"
                )

                # Remove lockdown info
                lockdown_data = await self.get_setting(ctx.guild_id, "lockdowns", {})
                if str(target_channel.id) in lockdown_data:
                    del lockdown_data[str(target_channel.id)]
                    await self.set_setting(ctx.guild_id, "lockdowns", lockdown_data)

                embed = self.create_embed(
                    title="🔓 Channel Unlocked",
                    description=f"{target_channel.mention} has been unlocked.",
                    color=hikari.Color(0x00FF00),
                )
                embed.add_field("Reason", reason, inline=False)
                embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "lockdown", True)

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage channel permissions.",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "lockdown", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in lockdown command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to {action} channel: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "lockdown", False, str(e))
