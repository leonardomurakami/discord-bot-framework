from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

from bot.plugins.commands import command

from ..config import (
    ERROR_COLOR,
    SERVER_FEATURE_MAPPING,
    SERVER_INFO_COLOR,
    UPTIME_COLOR,
)

if TYPE_CHECKING:
    from ..plugin import AdminPlugin

logger = logging.getLogger(__name__)


def setup_info_commands(plugin: AdminPlugin) -> list[Callable[..., Any]]:
    """Register informational admin commands."""

    @command(
        name="bot-info",
        description="Display bot information and statistics",
        aliases=["info"],
        permission_node="basic.admin.info.view",
    )
    async def bot_info(ctx: lightbulb.Context) -> None:
        try:
            overview = await plugin.bot.get_bot_overview()
            bot_user = overview.user

            embed = plugin.create_embed(
                title=f"🤖 {bot_user.username} Information",
                color=SERVER_INFO_COLOR,
            )

            embed.add_field("Guilds", str(overview.guild_count), inline=True)
            embed.add_field("Plugins Loaded", str(overview.plugin_count), inline=True)
            embed.add_field("Database", "✅ Connected" if overview.database_connected else "❌ Disconnected", inline=True)

            embed.set_thumbnail(bot_user.display_avatar_url)

            if bot_user.created_at:
                embed.set_footer(f"Created on {bot_user.created_at.strftime('%B %d, %Y')}")

            await plugin.respond_success(ctx, embed=embed, command_name="bot-info")

        except Exception as exc:
            logger.error("Error in bot-info command: %s", exc)
            await plugin.respond_error(
                ctx,
                f"Failed to get bot information: {exc}",
                command_name="bot-info",
                color=ERROR_COLOR,
            )

    @command(
        name="server-info",
        description="Display server information and statistics",
        aliases=["serverinfo", "guild-info"],
        permission_node="basic.admin.info.view",
    )
    async def server_info(ctx: lightbulb.Context) -> None:
        try:
            guild = ctx.get_guild()
            if not guild:
                await plugin.respond_error(
                    ctx,
                    "This command can only be used in a server.",
                    command_name="server-info",
                    color=ERROR_COLOR,
                )
                return

            summary = plugin.bot.summarise_guild(guild)

            embed = plugin.create_embed(title=f"🏰 {guild.name}", color=SERVER_INFO_COLOR)

            embed.add_field("Server ID", str(guild.id), inline=True)
            embed.add_field("Owner", f"<@{guild.owner_id}>", inline=True)
            embed.add_field("Created", f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)

            embed.add_field("👥 Members", str(summary.member_count), inline=True)
            embed.add_field("📺 Channels", f"{summary.channel_count} total", inline=True)
            embed.add_field("🎭 Roles", str(summary.role_count), inline=True)

            channel_breakdown = (
                f"💬 Text: {summary.text_channels}\n"
                f"🔊 Voice: {summary.voice_channels}\n"
                f"📁 Categories: {summary.category_channels}"
            )
            embed.add_field("Channel Breakdown", channel_breakdown, inline=True)
            embed.add_field("😀 Emojis", str(summary.emoji_count), inline=True)

            features = guild.features
            if features:
                feature_names: list[str] = []

                for feature in features:
                    if feature in SERVER_FEATURE_MAPPING:
                        feature_names.append(SERVER_FEATURE_MAPPING[feature])
                    elif len(feature_names) < 5:
                        feature_names.append(feature.replace("_", " ").title())

                if feature_names:
                    embed.add_field(
                        "✨ Features",
                        "\n".join(f"• {name}" for name in feature_names[:5]),
                        inline=False,
                    )

            icon_url = guild.make_icon_url()
            if icon_url:
                embed.set_thumbnail(icon_url)

            banner_url = guild.make_banner_url()
            if banner_url:
                embed.set_image(banner_url)

            await plugin.respond_success(ctx, embed=embed, command_name="server-info")

        except Exception as exc:
            logger.error("Error in server-info command: %s", exc)
            await plugin.respond_error(
                ctx,
                f"Failed to get server information: {exc}",
                command_name="server-info",
                color=ERROR_COLOR,
            )

    @command(
        name="uptime",
        description="Display bot uptime and system information",
        aliases=["up", "status"],
        permission_node="basic.admin.status.view",
    )
    async def uptime(ctx: lightbulb.Context) -> None:
        try:
            import time
            from datetime import datetime

            import psutil  # type: ignore

            process = psutil.Process()
            process_start_time = process.create_time()
            bot_start_time = datetime.fromtimestamp(process_start_time)

            current_time = datetime.now()
            uptime_delta = current_time - bot_start_time

            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            uptime_parts: list[str] = []
            if days > 0:
                uptime_parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                uptime_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                uptime_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if seconds > 0 or not uptime_parts:
                uptime_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

            formatted_uptime = ", ".join(uptime_parts)

            embed = plugin.create_embed(title="📊 Bot Status & Uptime", color=UPTIME_COLOR)

            embed.add_field("⏰ Uptime", formatted_uptime, inline=True)
            embed.add_field("🚀 Started", f"<t:{int(process_start_time)}:R>", inline=True)
            embed.add_field("📅 Current Time", f"<t:{int(current_time.timestamp())}:f>", inline=True)

            try:
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                embed.add_field("💾 Memory Usage", f"{memory_mb:.1f} MB", inline=True)
                embed.add_field("⚡ CPU Usage", f"{cpu_percent:.1f}%", inline=True)

                system_uptime = time.time() - psutil.boot_time()
                system_days = int(system_uptime // 86400)
                system_hours = int((system_uptime % 86400) // 3600)
                embed.add_field("🖥️ System Uptime", f"{system_days}d {system_hours}h", inline=True)

            except Exception:
                pass

            guild_count = len(plugin.cache.get_guilds_view()) if plugin.cache else 0
            embed.add_field("🏰 Servers", str(guild_count), inline=True)

            try:
                latency = plugin.gateway.heartbeat_latency * 1000
                embed.add_field("📡 Latency", f"{latency:.1f}ms", inline=True)
            except Exception:
                pass

            embed.set_footer(f"Process ID: {process.pid}")

            await plugin.respond_success(ctx, embed=embed, command_name="uptime")

        except ImportError:
            embed = plugin.create_embed(
                title="📊 Bot Status",
                description="Bot is online and responding!",
                color=UPTIME_COLOR,
            )

            guild_count = len(plugin.cache.get_guilds_view()) if plugin.cache else 0
            embed.add_field("🏰 Servers", str(guild_count), inline=True)

            try:
                latency = plugin.gateway.heartbeat_latency * 1000
                embed.add_field("📡 Latency", f"{latency:.1f}ms", inline=True)
            except Exception:
                pass

            embed.set_footer("Install 'psutil' for detailed system information")

            await plugin.respond_success(ctx, embed=embed, command_name="uptime")

        except Exception as exc:
            logger.error("Error in uptime command: %s", exc)
            await plugin.respond_error(
                ctx,
                f"Failed to get uptime information: {exc}",
                command_name="uptime",
                color=ERROR_COLOR,
            )

    return [bot_info, server_info, uptime]
