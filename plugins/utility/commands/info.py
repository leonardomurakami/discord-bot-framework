from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import ERROR_COLOR, INFO_COLOR, WEATHER_COLOR, WEATHER_FALLBACK_COLOR

if TYPE_CHECKING:
    from ..plugin import UtilityPlugin

logger = logging.getLogger(__name__)


def setup_info_commands(plugin: UtilityPlugin) -> list[Callable[..., Any]]:
    """Register informational utility commands."""

    @command(
        name="userinfo",
        description="Get detailed information about a user",
        aliases=["user", "whois"],
        permission_node="basic.utility.info.view",
        arguments=[
            CommandArgument(
                "user",
                hikari.OptionType.USER,
                "User to get information about",
                required=False,
            )
        ],
    )
    async def user_info(ctx: lightbulb.Context, user: hikari.User | None = None) -> None:
        try:
            target_user = user or ctx.author
            guild = ctx.get_guild()

            embed = plugin.create_embed(title=f"👤 {target_user.username}", color=INFO_COLOR)
            embed.add_field("User ID", str(target_user.id), inline=True)
            embed.add_field("Display Name", target_user.display_name, inline=True)
            embed.add_field("Bot Account", "Yes" if target_user.is_bot else "No", inline=True)
            embed.add_field(
                "Account Created",
                f"<t:{int(target_user.created_at.timestamp())}:R>",
                inline=True,
            )

            avatar_url = target_user.make_avatar_url()
            if avatar_url:
                embed.set_thumbnail(avatar_url)

            if guild:
                try:
                    member = plugin.bot.hikari_bot.cache.get_member(guild.id, target_user.id)
                    if not member:
                        member = await guild.fetch_member(target_user.id)

                    if member and member.joined_at:
                        embed.add_field(
                            "Joined Server",
                            f"<t:{int(member.joined_at.timestamp())}:R>",
                            inline=True,
                        )

                    if member:
                        roles = [f"<@&{role_id}>" for role_id in member.role_ids if role_id != guild.id]
                        if roles:
                            roles_text = " ".join(roles[:10])
                            if len(roles) > 10:
                                roles_text += f" (+{len(roles) - 10} more)"
                            embed.add_field("Roles", roles_text, inline=False)

                        try:
                            from bot.core.utils import calculate_member_permissions

                            permissions = calculate_member_permissions(member, guild)
                            key_permissions: list[str] = []
                            if permissions & hikari.Permissions.ADMINISTRATOR:
                                key_permissions.append("Administrator")
                            if permissions & hikari.Permissions.MANAGE_GUILD:
                                key_permissions.append("Manage Server")
                            if permissions & hikari.Permissions.MANAGE_CHANNELS:
                                key_permissions.append("Manage Channels")
                            if permissions & hikari.Permissions.MANAGE_MESSAGES:
                                key_permissions.append("Manage Messages")

                            if key_permissions:
                                embed.add_field("Key Permissions", ", ".join(key_permissions), inline=True)
                        except Exception:
                            pass
                except Exception:
                    pass

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "userinfo", True)

        except Exception as exc:
            logger.error("Error in userinfo command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to get user information: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "userinfo", False, str(exc))

    @command(
        name="avatar",
        description="Get a user's avatar in high resolution",
        aliases=["av", "pfp"],
        permission_node="basic.utility.info.view",
        arguments=[CommandArgument("user", hikari.OptionType.USER, "User to get avatar of", required=False)],
    )
    async def avatar(ctx: lightbulb.Context, user: hikari.User | None = None) -> None:
        try:
            target_user = user or ctx.author

            embed = plugin.create_embed(
                title=f"🖼️ {target_user.display_name}'s Avatar",
                color=INFO_COLOR,
            )

            avatar_url = target_user.display_avatar_url
            embed.set_image(avatar_url)
            embed.add_field("User", target_user.mention, inline=True)
            embed.add_field("Avatar URL", f"[Click here]({avatar_url})", inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "avatar", True)

        except Exception as exc:
            logger.error("Error in avatar command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to get avatar: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "avatar", False, str(exc))

    @command(
        name="weather",
        description="Get weather information for a location",
        permission_node="basic.utility.info.view",
        arguments=[
            CommandArgument(
                "location",
                hikari.OptionType.STRING,
                "City name or location to get weather for",
            )
        ],
    )
    async def weather_info(ctx: lightbulb.Context, location: str) -> None:
        try:
            if not plugin.session:
                embed = plugin.create_embed(
                    title="❌ Service Unavailable",
                    description="Weather service is currently unavailable.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            try:
                async with plugin.session.get(f"https://wttr.in/{location}?format=j1") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        current = data["current_condition"][0]
                        location_info = data["nearest_area"][0]

                        embed = plugin.create_embed(
                            title=(
                                "🌤️ Weather for " f"{location_info['areaName'][0]['value']}, {location_info['country'][0]['value']}"
                            ),
                            color=WEATHER_COLOR,
                        )

                        temp_c = current["temp_C"]
                        temp_f = current["temp_F"]
                        feels_like_c = current["FeelsLikeC"]
                        feels_like_f = current["FeelsLikeF"]

                        embed.add_field(
                            "🌡️ Temperature",
                            f"{temp_c}°C ({temp_f}°F)\nFeels like {feels_like_c}°C ({feels_like_f}°F)",
                            inline=True,
                        )
                        embed.add_field("☁️ Conditions", current["weatherDesc"][0]["value"], inline=True)
                        embed.add_field(
                            "💨 Wind",
                            f"{current['windspeedKmph']} km/h {current['winddir16Point']}",
                            inline=True,
                        )
                        embed.add_field("💧 Humidity", f"{current['humidity']}%", inline=True)
                        embed.add_field("👁️ Visibility", f"{current['visibility']} km", inline=True)
                        embed.add_field("🌡️ UV Index", current.get("uvIndex", "N/A"), inline=True)
                        embed.set_footer("Weather data provided by wttr.in")

                        await ctx.respond(embed=embed)
                        await plugin.log_command_usage(ctx, "weather", True)
                        return
            except Exception as exc:
                logger.error("Weather API error: %s", exc)

            embed = plugin.create_embed(
                title="🌤️ Weather Service",
                description=(
                    f"Weather information for '{location}' is currently unavailable. "
                    "Please try again later or check a weather website."
                ),
                color=WEATHER_FALLBACK_COLOR,
            )
            embed.add_field(
                "Suggested Alternatives",
                "• Check weather.com\n• Use your device's weather app\n• Try a different location name",
                inline=False,
            )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "weather", True)

        except Exception as exc:
            logger.error("Error in weather command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to get weather information. Try again later!",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "weather", False, str(exc))

    return [user_info, avatar, weather_info]
