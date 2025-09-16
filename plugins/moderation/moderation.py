import logging
from typing import Dict, Any
from datetime import datetime, timedelta
import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

logger = logging.getLogger(__name__)


class ModerationPlugin(BasePlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Moderation",
            "version": "1.0.0",
            "author": "Bot Framework",
            "description": "Moderation commands for server management",
            "permissions": [
                "moderation.kick",
                "moderation.ban",
                "moderation.mute",
                "moderation.warn",
                "moderation.purge",
                "moderation.timeout"
            ],
        }

    @command(
        name="kick",
        description="Kick a member from the server",
        permission_node="moderation.kick"
    )
    async def kick_member(self, ctx: lightbulb.Context) -> None:
        # Get member and reason from options or args
        member = None
        reason = "No reason provided"
        
        if hasattr(ctx, 'options'):
            member = getattr(ctx.options, 'member', None)
            reason = getattr(ctx.options, 'reason', "No reason provided")
        elif hasattr(ctx, 'args') and ctx.args:
            # For prefix commands, expect member mention/ID as first arg
            if len(ctx.args) >= 1:
                try:
                    member_id = int(ctx.args[0].strip('<@!>'))
                    member = ctx.get_guild().get_member(member_id)
                except (ValueError, AttributeError):
                    pass
            if len(ctx.args) >= 2:
                reason = " ".join(ctx.args[1:])
        
        if not member:
            embed = self.create_embed(
                title="❌ Invalid Member",
                description="Please specify a valid member to kick.",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            return
        try:
            if member.id == ctx.author.id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot kick yourself!",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.client.get_me().id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot kick myself!",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Try to send DM before kicking
            try:
                dm_channel = await member.fetch_dm_channel()
                embed_dm = self.create_embed(
                    title="🦵 You have been kicked",
                    description=f"You have been kicked from **{ctx.get_guild().name}**",
                    color=hikari.Color(0xFF6600)
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
                color=hikari.Color(0x00FF00)
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "kick", True)

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to kick this member. They might have higher roles than me.",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "kick", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in kick command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to kick member: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "kick", False, str(e))

    @command(
        name="ban",
        description="Ban a member from the server",
        permission_node="moderation.ban"
    )
    async def ban_member(self, ctx: lightbulb.Context) -> None:
        # Get user, delete_days, and reason from options or args
        user = None
        delete_days = 1
        reason = "No reason provided"
        
        if hasattr(ctx, 'options'):
            user = getattr(ctx.options, 'user', None)
            delete_days = getattr(ctx.options, 'delete_days', 1)
            reason = getattr(ctx.options, 'reason', "No reason provided")
        elif hasattr(ctx, 'args') and ctx.args:
            # For prefix commands, expect user mention/ID as first arg
            if len(ctx.args) >= 1:
                try:
                    user_id = int(ctx.args[0].strip('<@!>'))
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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            return
        try:
            if user.id == ctx.author.id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot ban yourself!",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if user.id == ctx.client.get_me().id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot ban myself!",
                    color=hikari.Color(0xFF0000)
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
                        color=hikari.Color(0xFF0000)
                    )
                    embed_dm.add_field("Reason", reason, inline=False)
                    embed_dm.add_field("Moderator", f"{ctx.author.mention}", inline=True)
                    await dm_channel.send(embed=embed_dm)
            except Exception:
                pass  # DM failed, continue with ban

            await ctx.get_guild().ban(
                user,
                delete_message_days=delete_days,
                reason=f"{reason} (by {ctx.author})"
            )

            embed = self.create_embed(
                title="✅ User Banned",
                description=f"{user.mention} has been banned from the server.",
                color=hikari.Color(0x00FF00)
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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "ban", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in ban command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to ban user: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "ban", False, str(e))

    @command(
        name="timeout",
        description="Timeout a member for a specified duration",
        permission_node="moderation.timeout"
    )
    async def timeout_member(self, ctx: lightbulb.Context) -> None:
        # Get member, duration, and reason from options or args
        member = None
        duration = 0
        reason = "No reason provided"
        
        if hasattr(ctx, 'options'):
            member = getattr(ctx.options, 'member', None)
            duration = getattr(ctx.options, 'duration', 0)
            reason = getattr(ctx.options, 'reason', "No reason provided")
        elif hasattr(ctx, 'args') and len(ctx.args) >= 2:
            # For prefix commands, expect member mention/ID and duration
            try:
                member_id = int(ctx.args[0].strip('<@!>'))
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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            return
        try:
            if member.id == ctx.author.id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot timeout yourself!",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.client.get_me().id:
                embed = self.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot timeout myself!",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Calculate timeout end time
            timeout_until = datetime.now() + timedelta(minutes=duration)

            await member.edit(
                communication_disabled_until=timeout_until,
                reason=f"{reason} (by {ctx.author})"
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
                color=hikari.Color(0x00FF00)
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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "timeout", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in timeout command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to timeout member: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "timeout", False, str(e))

    @command(
        name="purge",
        description="Delete multiple messages from a channel",
        aliases=["clear"],
        permission_node="moderation.purge",
        arguments=[
            CommandArgument("amount", hikari.OptionType.INTEGER, "Number of messages to delete (1-100)"),
            CommandArgument("user", hikari.OptionType.USER, "Only delete messages from this user", required=False)
        ]
    )
    async def purge_messages(self, ctx: lightbulb.Context, amount: int, user = None) -> None:
        if amount <= 0 or amount > 100:
            embed = self.create_embed(
                title="❌ Invalid Amount",
                description="Please specify a number between 1 and 100 messages to delete.",
                color=hikari.Color(0xFF0000)
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
                    color=hikari.Color(0x00FF00)
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
                    color=hikari.Color(0x00FF00)
                )

            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "purge", True)

        except hikari.ForbiddenError:
            embed = self.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages in this channel.",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "purge", False, "Permission denied")

        except Exception as e:
            logger.error(f"Error in purge command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to purge messages: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "purge", False, str(e))