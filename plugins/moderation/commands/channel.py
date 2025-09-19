from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import (
    ERROR_COLOR,
    LOCK_COLOR,
    LOCKDOWN_ACTIONS,
    NOTICE_COLOR,
    PURGE_MAX,
    PURGE_MIN,
    SLOWMODE_DISABLE_COLOR,
    SLOWMODE_ENABLE_COLOR,
    SLOWMODE_MAX_SECONDS,
    SUCCESS_COLOR,
)

if TYPE_CHECKING:
    from ..moderation_plugin import ModerationPlugin

logger = logging.getLogger(__name__)


def setup_channel_commands(plugin: "ModerationPlugin") -> list[Callable[..., Any]]:
    """Register channel-related moderation commands."""

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
    async def purge_messages(ctx: lightbulb.Context, amount: int, user: hikari.User | None = None) -> None:
        if amount < PURGE_MIN or amount > PURGE_MAX:
            embed = plugin.create_embed(
                title="❌ Invalid Amount",
                description=f"Please specify a number between {PURGE_MIN} and {PURGE_MAX} messages to delete.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            return

        try:
            channel = ctx.get_channel()
            await ctx.defer()

            if user:
                messages: list[hikari.Message] = []
                async for message in channel.fetch_history(limit=500):
                    if message.author.id == user.id:
                        messages.append(message)
                        if len(messages) >= amount:
                            break

                deleted_count = len(messages)
                if messages:
                    await channel.delete_messages(messages)

                embed = plugin.create_embed(
                    title="✅ Messages Purged",
                    description=f"Deleted {deleted_count} message(s) from {user.mention}.",
                    color=SUCCESS_COLOR,
                )
            else:
                messages: list[hikari.Message] = []
                async for message in channel.fetch_history(limit=amount):
                    messages.append(message)

                if messages:
                    await channel.delete_messages(messages)

                embed = plugin.create_embed(
                    title="✅ Messages Purged",
                    description=f"Deleted {len(messages)} message(s) from this channel.",
                    color=SUCCESS_COLOR,
                )

            embed.add_field("Moderator", ctx.author.mention, inline=True)
            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "purge", True)

        except hikari.ForbiddenError:
            embed = plugin.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages in this channel.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "purge", False, "Permission denied")

        except Exception as exc:
            logger.error("Error in purge command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to purge messages: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "purge", False, str(exc))

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
    async def slowmode(ctx: lightbulb.Context, seconds: int = 0, channel: hikari.GuildChannel | None = None) -> None:
        try:
            if seconds < 0 or seconds > SLOWMODE_MAX_SECONDS:
                embed = plugin.create_embed(
                    title="❌ Invalid Duration",
                    description=f"Slowmode must be between 0 and {SLOWMODE_MAX_SECONDS} seconds (6 hours).",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            target_channel = channel or ctx.get_channel()

            if target_channel.type not in (
                hikari.ChannelType.GUILD_TEXT,
                hikari.ChannelType.GUILD_NEWS,
            ):
                embed = plugin.create_embed(
                    title="❌ Invalid Channel",
                    description="Slowmode can only be applied to text channels.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await target_channel.edit(rate_limit_per_user=seconds)

            if seconds == 0:
                duration_text = "disabled"
                title_emoji = "🚫"
                title_text = "Slowmode Disabled"
                color = SLOWMODE_DISABLE_COLOR
            else:
                color = SLOWMODE_ENABLE_COLOR
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

            embed = plugin.create_embed(
                title=f"{title_emoji} {title_text}",
                description=f"Slowmode has been set to **{duration_text}** in {target_channel.mention}.",
                color=color,
            )
            embed.add_field("Channel", target_channel.mention, inline=True)
            embed.add_field("Duration", duration_text, inline=True)
            embed.add_field("Moderator", ctx.author.mention, inline=True)

            if seconds > 0:
                embed.set_footer("Users must wait between sending messages in this channel")

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "slowmode", True)

        except hikari.ForbiddenError:
            embed = plugin.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "slowmode", False, "Permission denied")

        except Exception as exc:
            logger.error("Error in slowmode command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to set slowmode: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "slowmode", False, str(exc))

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
    async def lockdown_channel(
        ctx: lightbulb.Context,
        action: str,
        channel: hikari.GuildChannel | None = None,
        reason: str = "No reason provided",
    ) -> None:
        try:
            if not ctx.guild_id:
                embed = plugin.create_embed(
                    title="❌ Server Only",
                    description="This command can only be used in a server.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            action = action.lower().strip()
            if action not in LOCKDOWN_ACTIONS:
                embed = plugin.create_embed(
                    title="❌ Invalid Action",
                    description="Valid actions are: `lock`, `unlock`",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            target_channel = channel or ctx.get_channel()

            if target_channel.type not in (
                hikari.ChannelType.GUILD_TEXT,
                hikari.ChannelType.GUILD_NEWS,
            ):
                embed = plugin.create_embed(
                    title="❌ Invalid Channel",
                    description="Lockdown can only be applied to text channels.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            guild = ctx.get_guild()
            everyone_role = guild.get_role(ctx.guild_id)

            if not everyone_role:
                embed = plugin.create_embed(
                    title="❌ Permission Error",
                    description="Could not find @everyone role.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if action == "lock":
                await target_channel.edit_overwrite(
                    everyone_role,
                    deny=hikari.Permissions.SEND_MESSAGES,
                    reason=f"Channel lockdown: {reason} (by {ctx.author})",
                )

                lockdown_data = await plugin.get_setting(ctx.guild_id, "lockdowns", {})
                lockdown_data[str(target_channel.id)] = {
                    "moderator": ctx.author.id,
                    "reason": reason,
                    "timestamp": int(datetime.now().timestamp()),
                }
                await plugin.set_setting(ctx.guild_id, "lockdowns", lockdown_data)

                embed = plugin.create_embed(
                    title="🔒 Channel Locked",
                    description=f"{target_channel.mention} has been locked down.",
                    color=LOCK_COLOR,
                )
                embed.add_field("Reason", reason, inline=False)
                embed.add_field("Moderator", ctx.author.mention, inline=True)
            else:
                await target_channel.edit_overwrite(
                    everyone_role,
                    allow=hikari.Permissions.SEND_MESSAGES,
                    reason=f"Channel unlock: {reason} (by {ctx.author})",
                )

                lockdown_data = await plugin.get_setting(ctx.guild_id, "lockdowns", {})
                if str(target_channel.id) in lockdown_data:
                    del lockdown_data[str(target_channel.id)]
                    await plugin.set_setting(ctx.guild_id, "lockdowns", lockdown_data)

                embed = plugin.create_embed(
                    title="🔓 Channel Unlocked",
                    description=f"{target_channel.mention} has been unlocked.",
                    color=SUCCESS_COLOR,
                )
                embed.add_field("Reason", reason, inline=False)
                embed.add_field("Moderator", ctx.author.mention, inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "lockdown", True)

        except hikari.ForbiddenError:
            embed = plugin.create_embed(
                title="❌ Permission Error",
                description="I don't have permission to manage channel permissions.",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "lockdown", False, "Permission denied")

        except Exception as exc:
            logger.error("Error in lockdown command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to {action} channel: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "lockdown", False, str(exc))

    return [purge_messages, slowmode, lockdown_channel]

