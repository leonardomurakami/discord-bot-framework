from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import (
    BAN_DM_COLOR,
    ERROR_COLOR,
    KICK_DM_COLOR,
    NOTICE_COLOR,
    SUCCESS_COLOR,
)

if TYPE_CHECKING:
    from ..moderation_plugin import ModerationPlugin

logger = logging.getLogger(__name__)


def _extract_member_from_context(ctx: lightbulb.Context) -> tuple[hikari.Member | None, str]:
    member = None
    reason = "No reason provided"

    if hasattr(ctx, "options"):
        member = getattr(ctx.options, "member", None)
        reason = getattr(ctx.options, "reason", reason)
    elif getattr(ctx, "args", None):
        args = ctx.args
        if len(args) >= 1:
            try:
                member_id = int(args[0].strip("<@!>"))
                member = ctx.get_guild().get_member(member_id)
            except (ValueError, AttributeError):
                member = None
        if len(args) >= 2:
            reason = " ".join(args[1:])

    return member, reason


def _extract_user_from_context(ctx: lightbulb.Context) -> tuple[int | None, hikari.User | None, int, str]:
    user = None
    delete_days = 1
    reason = "No reason provided"
    user_id: int | None = None

    if hasattr(ctx, "options"):
        user = getattr(ctx.options, "user", None)
        delete_days = getattr(ctx.options, "delete_days", delete_days)
        reason = getattr(ctx.options, "reason", reason)
    elif getattr(ctx, "args", None):
        args = ctx.args
        if len(args) >= 1:
            try:
                user_id = int(args[0].strip("<@!>"))
            except (ValueError, AttributeError):
                user_id = None
        if len(args) >= 2:
            try:
                delete_days = int(args[1])
            except ValueError:
                delete_days = 1
        if len(args) >= 3:
            reason = " ".join(args[2:])

    return user_id, user, delete_days, reason


def setup_action_commands(plugin: "ModerationPlugin") -> list[Callable[..., Any]]:
    """Register core moderation action commands."""

    @command(
        name="kick",
        description="Kick a member from the server",
        permission_node="moderation.kick",
    )
    async def kick_member(ctx: lightbulb.Context) -> None:
        member, reason = _extract_member_from_context(ctx)

        if not member:
            embed = plugin.create_embed(
                title="❌ Invalid Member",
                description="Please specify a valid member to kick.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            return

        try:
            if member.id == ctx.author.id:
                embed = plugin.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot kick yourself!",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.client.get_me().id:
                embed = plugin.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot kick myself!",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            try:
                dm_channel = await member.fetch_dm_channel()
                embed_dm = plugin.create_embed(
                    title="🦵 You have been kicked",
                    description=f"You have been kicked from **{ctx.get_guild().name}**",
                    color=KICK_DM_COLOR,
                )
                embed_dm.add_field("Reason", reason, inline=False)
                embed_dm.add_field("Moderator", f"{ctx.author.mention}", inline=True)
                await dm_channel.send(embed=embed_dm)
            except Exception:
                pass

            await ctx.get_guild().kick(member, reason=f"{reason} (by {ctx.author})")

            embed = plugin.create_embed(
                title="✅ Member Kicked",
                description=f"{member.mention} has been kicked from the server.",
                color=SUCCESS_COLOR,
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "kick", True)

        except hikari.ForbiddenError:
            embed = plugin.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to kick this member. They might have higher roles than me.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "kick", False, "Permission denied")

        except Exception as exc:
            logger.error("Error in kick command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to kick member: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "kick", False, str(exc))

    @command(
        name="ban",
        description="Ban a member from the server",
        permission_node="moderation.ban",
    )
    async def ban_member(ctx: lightbulb.Context) -> None:
        user_id, user, delete_days, reason = _extract_user_from_context(ctx)

        if not user and user_id is not None:
            try:
                user = await plugin.bot.hikari_bot.rest.fetch_user(user_id)
            except Exception:
                user = None

        if not user:
            embed = plugin.create_embed(
                title="❌ Invalid User",
                description="Please specify a valid user to ban.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            return

        try:
            if user.id == ctx.author.id:
                embed = plugin.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot ban yourself!",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if user.id == ctx.client.get_me().id:
                embed = plugin.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot ban myself!",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            try:
                member = ctx.get_guild().get_member(user.id)
                if member:
                    dm_channel = await user.fetch_dm_channel()
                    embed_dm = plugin.create_embed(
                        title="🔨 You have been banned",
                        description=f"You have been banned from **{ctx.get_guild().name}**",
                        color=BAN_DM_COLOR,
                    )
                    embed_dm.add_field("Reason", reason, inline=False)
                    embed_dm.add_field("Moderator", f"{ctx.author.mention}", inline=True)
                    await dm_channel.send(embed=embed_dm)
            except Exception:
                pass

            await ctx.get_guild().ban(
                user,
                delete_message_days=delete_days,
                reason=f"{reason} (by {ctx.author})",
            )

            embed = plugin.create_embed(
                title="✅ User Banned",
                description=f"{user.mention} has been banned from the server.",
                color=SUCCESS_COLOR,
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Messages Deleted", f"{delete_days} days", inline=True)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "ban", True)

        except hikari.ForbiddenError:
            embed = plugin.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to ban this user. They might have higher roles than me.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "ban", False, "Permission denied")

        except Exception as exc:
            logger.error("Error in ban command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to ban user: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "ban", False, str(exc))

    @command(
        name="timeout",
        description="Timeout a member for a specified duration",
        permission_node="moderation.timeout",
    )
    async def timeout_member(ctx: lightbulb.Context) -> None:
        member = None
        duration = 0
        reason = "No reason provided"

        if hasattr(ctx, "options"):
            member = getattr(ctx.options, "member", None)
            duration = getattr(ctx.options, "duration", duration)
            reason = getattr(ctx.options, "reason", reason)
        elif getattr(ctx, "args", None) and len(ctx.args) >= 2:
            try:
                member_id = int(ctx.args[0].strip("<@!>"))
                member = ctx.get_guild().get_member(member_id)
                duration = int(ctx.args[1])
            except (ValueError, AttributeError):
                member = None
            if len(ctx.args) >= 3:
                reason = " ".join(ctx.args[2:])

        if not member or duration <= 0:
            embed = plugin.create_embed(
                title="❌ Invalid Parameters",
                description="Please specify a valid member and duration in minutes.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            return

        try:
            if member.id == ctx.author.id:
                embed = plugin.create_embed(
                    title="❌ Invalid Target",
                    description="You cannot timeout yourself!",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.client.get_me().id:
                embed = plugin.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot timeout myself!",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            timeout_until = datetime.now() + timedelta(minutes=duration)

            await member.edit(
                communication_disabled_until=timeout_until,
                reason=f"{reason} (by {ctx.author})",
            )

            if duration < 60:
                duration_str = f"{duration} minute(s)"
            else:
                hours = duration // 60
                minutes = duration % 60
                duration_str = f"{hours} hour(s)"
                if minutes > 0:
                    duration_str += f" and {minutes} minute(s)"

            embed = plugin.create_embed(
                title="✅ Member Timed Out",
                description=f"{member.mention} has been timed out for {duration_str}.",
                color=SUCCESS_COLOR,
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Duration", duration_str, inline=True)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "timeout", True)

        except hikari.ForbiddenError:
            embed = plugin.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to timeout this member. They might have higher roles than me.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "timeout", False, "Permission denied")

        except Exception as exc:
            logger.error("Error in timeout command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to timeout member: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "timeout", False, str(exc))

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
    async def unban_user(ctx: lightbulb.Context, user_id: str, reason: str = "No reason provided") -> None:
        try:
            try:
                user_id_int = int(user_id.strip("<@!>"))
            except ValueError:
                embed = plugin.create_embed(
                    title="❌ Invalid User ID",
                    description="Please provide a valid user ID or mention.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            banned_user = None
            try:
                async for ban in ctx.get_guild().fetch_bans():
                    if ban.user.id == user_id_int:
                        banned_user = ban.user
                        break
                else:
                    embed = plugin.create_embed(
                        title="❌ User Not Banned",
                        description="This user is not currently banned from the server.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return
            except hikari.ForbiddenError:
                embed = plugin.create_embed(
                    title="❌ Permission Error",
                    description="I don't have permission to view the ban list.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await ctx.get_guild().unban(user_id_int, reason=f"{reason} (by {ctx.author})")

            embed = plugin.create_embed(
                title="✅ User Unbanned",
                description=f"{banned_user.mention} ({banned_user.username}) has been unbanned.",
                color=SUCCESS_COLOR,
            )
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Moderator", ctx.author.mention, inline=True)
            embed.add_field("User ID", str(user_id_int), inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "unban", True)

        except hikari.NotFoundError:
            embed = plugin.create_embed(
                title="❌ User Not Found",
                description="User not found in the ban list or invalid user ID.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "unban", False, "User not found")

        except hikari.ForbiddenError:
            embed = plugin.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to unban users.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "unban", False, "Permission denied")

        except Exception as exc:
            logger.error("Error in unban command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to unban user: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "unban", False, str(exc))

    @command(
        name="nickname",
        description="Change a member's server nickname",
        permission_node="moderation.nickname",
        arguments=[
            CommandArgument(
                "member",
                hikari.OptionType.USER,
                "Member to change nickname for",
            ),
            CommandArgument(
                "nickname",
                hikari.OptionType.STRING,
                "New nickname (leave empty to remove nickname)",
                required=False,
            ),
            CommandArgument(
                "reason",
                hikari.OptionType.STRING,
                "Reason for nickname change",
                required=False,
                default="No reason provided",
            ),
        ],
    )
    async def change_nickname(ctx: lightbulb.Context, member: hikari.User, nickname: str | None = None, reason: str = "No reason provided") -> None:
        try:
            if not ctx.guild_id:
                embed = plugin.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            guild_member = ctx.get_guild().get_member(member.id)
            if not guild_member:
                embed = plugin.create_embed(
                    title="❌ Member Not Found",
                    description="The specified member is not in this server.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if member.id == ctx.client.get_me().id:
                embed = plugin.create_embed(
                    title="❌ Invalid Target",
                    description="I cannot change my own nickname through this command!",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            old_nickname = guild_member.display_name

            # If nickname is None or empty string, we're removing the nickname
            new_nickname = nickname.strip() if nickname else None

            await guild_member.edit(
                nickname=new_nickname,
                reason=f"{reason} (by {ctx.author})",
            )

            if new_nickname:
                title = "✅ Nickname Changed"
            else:
                title = "✅ Nickname Removed"

            embed = plugin.create_embed(
                title=title,
                description=f"{member.mention}'s nickname has been updated.",
                color=SUCCESS_COLOR,
            )
            embed.add_field("Previous Nickname", old_nickname, inline=True)
            embed.add_field("New Nickname", new_nickname or "None", inline=True)
            embed.add_field("Reason", reason, inline=False)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "nickname", True)

        except hikari.ForbiddenError:
            embed = plugin.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to change this member's nickname. They might have higher roles than me.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "nickname", False, "Permission denied")

        except Exception as exc:
            logger.error("Error in nickname command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to change nickname: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "nickname", False, str(exc))

    return [kick_member, ban_member, timeout_member, unban_user, change_nickname]
