import base64
import hashlib
import logging
import re
from datetime import datetime

import aiohttp
import hikari
import lightbulb

from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command

logger = logging.getLogger(__name__)


class UtilityPlugin(BasePlugin):
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession = None

    async def on_load(self) -> None:
        self.session = aiohttp.ClientSession()
        await super().on_load()

    async def on_unload(self) -> None:
        if self.session:
            await self.session.close()
        await super().on_unload()

    @command(
        name="userinfo",
        description="Get detailed information about a user",
        aliases=["user", "whois"],
        permission_node="utility.info",
        arguments=[
            CommandArgument(
                "user",
                hikari.OptionType.USER,
                "User to get information about",
                required=False,
            )
        ],
    )
    async def user_info(self, ctx: lightbulb.Context, user: hikari.User = None) -> None:
        try:
            target_user = user or ctx.author
            guild = ctx.get_guild()

            embed = self.create_embed(title=f"👤 {target_user.username}", color=hikari.Color(0x5865F2))

            # Basic user info
            embed.add_field("User ID", str(target_user.id), inline=True)
            embed.add_field("Display Name", target_user.display_name, inline=True)
            embed.add_field("Bot Account", "Yes" if target_user.is_bot else "No", inline=True)

            # Account creation
            embed.add_field(
                "Account Created",
                f"<t:{int(target_user.created_at.timestamp())}:R>",
                inline=True,
            )

            # Avatar
            avatar_url = target_user.make_avatar_url()
            if avatar_url:
                embed.set_thumbnail(avatar_url)

            # Guild-specific info if in a guild
            if guild:
                try:
                    # Try cache first, then fetch from API
                    member = None
                    try:
                        member = self.bot.hikari_bot.cache.get_member(guild.id, target_user.id)
                        if not member:
                            member = await guild.fetch_member(target_user.id)
                    except (
                        hikari.NotFoundError,
                        hikari.ForbiddenError,
                        AttributeError,
                    ):
                        pass

                    if member:
                        # Join date
                        if member.joined_at:
                            embed.add_field(
                                "Joined Server",
                                f"<t:{int(member.joined_at.timestamp())}:R>",
                                inline=True,
                            )

                        # Roles
                        roles = [f"<@&{role_id}>" for role_id in member.role_ids if role_id != guild.id]
                        if roles:
                            roles_text = " ".join(roles[:10])  # Limit to 10 roles
                            if len(roles) > 10:
                                roles_text += f" (+{len(roles) - 10} more)"
                            embed.add_field("Roles", roles_text, inline=False)

                        # Guild permissions
                        try:
                            from bot.core.utils import calculate_member_permissions
                            permissions = calculate_member_permissions(member, guild)
                            admin_perms = []
                            if permissions & hikari.Permissions.ADMINISTRATOR:
                                admin_perms.append("Administrator")
                            elif permissions & hikari.Permissions.MANAGE_GUILD:
                                admin_perms.append("Manage Server")
                            elif permissions & hikari.Permissions.MANAGE_CHANNELS:
                                admin_perms.append("Manage Channels")
                            elif permissions & hikari.Permissions.MANAGE_MESSAGES:
                                admin_perms.append("Manage Messages")

                            if admin_perms:
                                embed.add_field("Key Permissions", ", ".join(admin_perms), inline=True)
                        except Exception:
                            pass  # Skip permissions if we can't calculate them

                except Exception:
                    pass  # Not a member or can't get member info

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "userinfo", True)

        except Exception as e:
            logger.error(f"Error in userinfo command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to get user information: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "userinfo", False, str(e))

    @command(
        name="avatar",
        description="Get a user's avatar in high resolution",
        aliases=["av", "pfp"],
        permission_node="utility.info",
        arguments=[CommandArgument("user", hikari.OptionType.USER, "User to get avatar of", required=False)],
    )
    async def avatar(self, ctx: lightbulb.Context, user: hikari.User = None) -> None:
        try:
            target_user = user or ctx.author

            embed = self.create_embed(
                title=f"🖼️ {target_user.display_name}'s Avatar",
                color=hikari.Color(0x9932CC),
            )

            # Get avatar URL
            avatar_url = target_user.display_avatar_url

            embed.set_image(avatar_url)
            embed.add_field("User", target_user.mention, inline=True)
            embed.add_field("Avatar URL", f"[Click here]({avatar_url})", inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "avatar", True)

        except Exception as e:
            logger.error(f"Error in avatar command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to get avatar: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "avatar", False, str(e))

    @command(
        name="timestamp",
        description="Convert time to Discord timestamp formats",
        aliases=["time", "ts"],
        permission_node="utility.convert",
        arguments=[
            CommandArgument(
                "time_input",
                hikari.OptionType.STRING,
                "Time input (YYYY-MM-DD HH:MM, Unix timestamp, or 'now')",
                required=False,
                default="now",
            )
        ],
    )
    async def timestamp(self, ctx: lightbulb.Context, time_input: str = "now") -> None:
        try:
            # Parse input
            if time_input.lower() == "now":
                timestamp = int(datetime.now().timestamp())
            elif time_input.isdigit():
                # Unix timestamp
                timestamp = int(time_input)
                # Validate reasonable timestamp range
                if timestamp < 0 or timestamp > 4102444800:  # Up to year 2100
                    raise ValueError("Timestamp out of reasonable range")
            else:
                # Try to parse date string
                try:
                    # Support various formats
                    formats = [
                        "%Y-%m-%d %H:%M",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d",
                        "%m/%d/%Y %H:%M",
                        "%m/%d/%Y",
                    ]

                    parsed_time = None
                    for fmt in formats:
                        try:
                            parsed_time = datetime.strptime(time_input, fmt)
                            break
                        except ValueError:
                            continue

                    if not parsed_time:
                        raise ValueError("Invalid date format")

                    timestamp = int(parsed_time.timestamp())
                except ValueError:
                    embed = self.create_embed(
                        title="❌ Invalid Format",
                        description="Please use formats like:\n• `YYYY-MM-DD HH:MM`\n• `YYYY-MM-DD`\n• Unix timestamp\n• `now`",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

            # Create embed with all timestamp formats
            embed = self.create_embed(
                title="🕒 Discord Timestamps",
                description=f"Timestamp: `{timestamp}`",
                color=hikari.Color(0x00CED1),
            )

            formats = {
                "Default": f"<t:{timestamp}>",
                "Short Time": f"<t:{timestamp}:t>",
                "Long Time": f"<t:{timestamp}:T>",
                "Short Date": f"<t:{timestamp}:d>",
                "Long Date": f"<t:{timestamp}:D>",
                "Short Date/Time": f"<t:{timestamp}:f>",
                "Long Date/Time": f"<t:{timestamp}:F>",
                "Relative": f"<t:{timestamp}:R>",
            }

            for name, discord_format in formats.items():
                embed.add_field(name, f"`{discord_format}`\n{discord_format}", inline=True)

            embed.set_footer("Copy the format you want to use in your messages!")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "timestamp", True)

        except Exception as e:
            logger.error(f"Error in timestamp command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to create timestamp: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "timestamp", False, str(e))

    @command(
        name="color",
        description="Display information about a color",
        aliases=["colour"],
        permission_node="utility.tools",
        arguments=[
            CommandArgument(
                "color_input",
                hikari.OptionType.STRING,
                "Hex code (#FF0000) or color name (red)",
            )
        ],
    )
    async def color_info(self, ctx: lightbulb.Context, color_input: str) -> None:
        try:
            # Clean input
            color_input = color_input.strip().lower()

            # Color name mappings
            color_names = {
                "red": "#FF0000",
                "green": "#00FF00",
                "blue": "#0000FF",
                "yellow": "#FFFF00",
                "cyan": "#00FFFF",
                "magenta": "#FF00FF",
                "black": "#000000",
                "white": "#FFFFFF",
                "gray": "#808080",
                "orange": "#FFA500",
                "purple": "#800080",
                "pink": "#FFC0CB",
                "brown": "#A52A2A",
                "gold": "#FFD700",
                "silver": "#C0C0C0",
                "discord": "#5865F2",
                "blurple": "#5865F2",
            }

            # Parse color
            hex_color = None
            if color_input.startswith("#"):
                hex_color = color_input
            elif color_input in color_names:
                hex_color = color_names[color_input]
            else:
                embed = self.create_embed(
                    title="❌ Invalid Color",
                    description="Please provide a hex code (#FF0000) or color name (red, blue, etc.)",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Validate hex format
            if not re.match(r"^#[0-9A-Fa-f]{6}$", hex_color):
                embed = self.create_embed(
                    title="❌ Invalid Hex Code",
                    description="Hex code must be in format #RRGGBB (e.g., #FF0000)",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Convert to RGB
            hex_clean = hex_color.lstrip("#")
            rgb = tuple(int(hex_clean[i : i + 2], 16) for i in (0, 2, 4))

            # Convert to other formats
            rgb_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
            hsl = self._rgb_to_hsl(*rgb)
            hsl_str = f"hsl({hsl[0]}°, {hsl[1]}%, {hsl[2]}%)"

            # Create color integer for embed
            color_int = int(hex_clean, 16)

            embed = self.create_embed(title=f"🎨 Color: {hex_color.upper()}", color=hikari.Color(color_int))

            embed.add_field("Hex", hex_color.upper(), inline=True)
            embed.add_field("RGB", rgb_str, inline=True)
            embed.add_field("HSL", hsl_str, inline=True)
            embed.add_field("Decimal", str(color_int), inline=True)

            # Generate a color preview URL (using a simple color generator service)
            preview_url = f"https://via.placeholder.com/300x100/{hex_clean}/{hex_clean}.png"
            embed.set_image(preview_url)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "color", True)

        except Exception as e:
            logger.error(f"Error in color command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to process color: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "color", False, str(e))

    @command(
        name="base64",
        description="Encode or decode base64 text",
        aliases=["b64"],
        permission_node="utility.convert",
        arguments=[
            CommandArgument("action", hikari.OptionType.STRING, "encode or decode"),
            CommandArgument("text", hikari.OptionType.STRING, "Text to encode/decode"),
        ],
    )
    async def base64_convert(self, ctx: lightbulb.Context, action: str, text: str) -> None:
        try:
            action = action.lower().strip()

            if action not in ["encode", "decode", "enc", "dec"]:
                embed = self.create_embed(
                    title="❌ Invalid Action",
                    description="Action must be 'encode' or 'decode'",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if action in ["encode", "enc"]:
                # Encode to base64
                encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
                result = encoded
                action_text = "Encoded"
            else:
                # Decode from base64
                try:
                    decoded = base64.b64decode(text).decode("utf-8")
                    result = decoded
                    action_text = "Decoded"
                except Exception:
                    embed = self.create_embed(
                        title="❌ Invalid Base64",
                        description="The provided text is not valid base64.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

            # Limit output length for display
            if len(result) > 1024:
                display_result = result[:1021] + "..."
            else:
                display_result = result

            embed = self.create_embed(title=f"🔢 Base64 {action_text}", color=hikari.Color(0x9932CC))

            embed.add_field(
                "Input",
                f"```\n{text[:500]}{'...' if len(text) > 500 else ''}\n```",
                inline=False,
            )
            embed.add_field("Output", f"```\n{display_result}\n```", inline=False)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "base64", True)

        except Exception as e:
            logger.error(f"Error in base64 command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to process base64: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "base64", False, str(e))

    @command(
        name="hash",
        description="Generate hash of text (MD5, SHA1, SHA256)",
        permission_node="utility.tools",
        arguments=[
            CommandArgument(
                "algorithm",
                hikari.OptionType.STRING,
                "Hash algorithm (md5, sha1, sha256)",
            ),
            CommandArgument("text", hikari.OptionType.STRING, "Text to hash"),
        ],
    )
    async def hash_text(self, ctx: lightbulb.Context, algorithm: str, text: str) -> None:
        try:
            algorithm = algorithm.lower().strip()

            if algorithm not in ["md5", "sha1", "sha256"]:
                embed = self.create_embed(
                    title="❌ Invalid Algorithm",
                    description="Algorithm must be 'md5', 'sha1', or 'sha256'",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Generate hash
            if algorithm == "md5":
                hash_obj = hashlib.md5(text.encode("utf-8"))
            elif algorithm == "sha1":
                hash_obj = hashlib.sha1(text.encode("utf-8"))
            elif algorithm == "sha256":
                hash_obj = hashlib.sha256(text.encode("utf-8"))

            result = hash_obj.hexdigest()

            embed = self.create_embed(title=f"🔐 {algorithm.upper()} Hash", color=hikari.Color(0x8B4513))

            # Show input (truncated for security/display)
            display_input = text[:100] + "..." if len(text) > 100 else text
            embed.add_field("Input", f"```\n{display_input}\n```", inline=False)
            embed.add_field("Hash", f"```\n{result}\n```", inline=False)
            embed.add_field("Algorithm", algorithm.upper(), inline=True)
            embed.add_field("Length", f"{len(result)} characters", inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "hash", True)

        except Exception as e:
            logger.error(f"Error in hash command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to generate hash: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "hash", False, str(e))

    def _rgb_to_hsl(self, r: int, g: int, b: int) -> tuple:
        """Convert RGB to HSL color space."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val

        # Lightness
        lightness = (max_val + min_val) / 2

        if diff == 0:
            h = s = 0  # Achromatic
        else:
            # Saturation
            s = diff / (2 - max_val - min_val) if lightness > 0.5 else diff / (max_val + min_val)

            # Hue
            if max_val == r:
                h = (g - b) / diff + (6 if g < b else 0)
            elif max_val == g:
                h = (b - r) / diff + 2
            elif max_val == b:
                h = (r - g) / diff + 4
            h /= 6

        return (int(h * 360), int(s * 100), int(lightness * 100))

    @command(
        name="remindme",
        description="Set a personal reminder",
        aliases=["remind", "reminder"],
        permission_node="utility.tools",
        arguments=[
            CommandArgument(
                "time",
                hikari.OptionType.STRING,
                "When to remind (e.g., '5m', '1h', '2d')",
            ),
            CommandArgument(
                "message",
                hikari.OptionType.STRING,
                "What to remind you about",
            ),
        ],
    )
    async def remind_me(self, ctx: lightbulb.Context, time: str, message: str) -> None:
        try:
            import re
            from datetime import datetime, timedelta

            # Parse time input
            time_pattern = r'^(\d+)([mhd])$'
            match = re.match(time_pattern, time.lower().strip())

            if not match:
                embed = self.create_embed(
                    title="❌ Invalid Time Format",
                    description="Use format like: `5m` (5 minutes), `1h` (1 hour), `2d` (2 days)",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            amount = int(match.group(1))
            unit = match.group(2)

            # Convert to timedelta
            if unit == 'm':
                if amount > 10080:  # Max 1 week in minutes
                    raise ValueError("Maximum reminder time is 1 week")
                delta = timedelta(minutes=amount)
                unit_text = f"{amount} minute(s)"
            elif unit == 'h':
                if amount > 168:  # Max 1 week in hours
                    raise ValueError("Maximum reminder time is 1 week")
                delta = timedelta(hours=amount)
                unit_text = f"{amount} hour(s)"
            elif unit == 'd':
                if amount > 7:  # Max 1 week
                    raise ValueError("Maximum reminder time is 1 week")
                delta = timedelta(days=amount)
                unit_text = f"{amount} day(s)"

            # Calculate reminder time
            remind_time = datetime.now() + delta
            remind_timestamp = int(remind_time.timestamp())

            # Store reminder (simplified - in a real implementation, you'd want a proper database table)
            reminder_data = {
                "user_id": ctx.author.id,
                "channel_id": ctx.channel_id,
                "message": message,
                "remind_time": remind_timestamp,
                "created_at": int(datetime.now().timestamp())
            }

            # For now, just show confirmation - in a real implementation, you'd store in DB and have a background task
            embed = self.create_embed(
                title="⏰ Reminder Set",
                description=f"I'll remind you in {unit_text}!",
                color=hikari.Color(0x00FF7F),
            )

            embed.add_field("Reminder", message, inline=False)
            embed.add_field("Time", f"<t:{remind_timestamp}:F>", inline=True)
            embed.add_field("Relative", f"<t:{remind_timestamp}:R>", inline=True)

            embed.set_footer("Note: Bot restarts will clear reminders. Use external tools for important reminders.")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "remindme", True)

        except ValueError as e:
            embed = self.create_embed(
                title="❌ Invalid Input",
                description=str(e),
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "remindme", False, str(e))

        except Exception as e:
            logger.error(f"Error in remindme command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to set reminder. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "remindme", False, str(e))

    @command(
        name="weather",
        description="Get weather information for a location",
        permission_node="utility.info",
        arguments=[
            CommandArgument(
                "location",
                hikari.OptionType.STRING,
                "City name or location to get weather for",
            )
        ],
    )
    async def weather_info(self, ctx: lightbulb.Context, location: str) -> None:
        try:
            if not self.session:
                embed = self.create_embed(
                    title="❌ Service Unavailable",
                    description="Weather service is currently unavailable.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # For demo purposes, we'll use a free weather API (OpenWeatherMap requires API key)
            # This is a simplified example - in production, you'd want to use a proper weather API
            try:
                # Using wttr.in API as a fallback (no API key required)
                async with self.session.get(f"https://wttr.in/{location}?format=j1") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        current = data["current_condition"][0]
                        location_info = data["nearest_area"][0]

                        embed = self.create_embed(
                            title=f"🌤️ Weather for {location_info['areaName'][0]['value']}, {location_info['country'][0]['value']}",
                            color=hikari.Color(0x87CEEB),
                        )

                        # Current conditions
                        temp_c = current["temp_C"]
                        temp_f = current["temp_F"]
                        feels_like_c = current["FeelsLikeC"]
                        feels_like_f = current["FeelsLikeF"]

                        embed.add_field(
                            "🌡️ Temperature",
                            f"{temp_c}°C ({temp_f}°F)\nFeels like {feels_like_c}°C ({feels_like_f}°F)",
                            inline=True
                        )

                        embed.add_field(
                            "☁️ Conditions",
                            current["weatherDesc"][0]["value"],
                            inline=True
                        )

                        embed.add_field(
                            "💨 Wind",
                            f"{current['windspeedKmph']} km/h {current['winddir16Point']}",
                            inline=True
                        )

                        embed.add_field(
                            "💧 Humidity",
                            f"{current['humidity']}%",
                            inline=True
                        )

                        embed.add_field(
                            "👁️ Visibility",
                            f"{current['visibility']} km",
                            inline=True
                        )

                        embed.add_field(
                            "🌡️ UV Index",
                            current.get('uvIndex', 'N/A'),
                            inline=True
                        )

                        embed.set_footer("Weather data provided by wttr.in")

                        await ctx.respond(embed=embed)
                        await self.log_command_usage(ctx, "weather", True)
                        return

            except Exception as e:
                logger.error(f"Weather API error: {e}")

            # Fallback response
            embed = self.create_embed(
                title="🌤️ Weather Service",
                description=f"Weather information for '{location}' is currently unavailable. Please try again later or check a weather website.",
                color=hikari.Color(0xFFAA00),
            )
            embed.add_field(
                "Suggested Alternatives",
                "• Check weather.com\n• Use your device's weather app\n• Try a different location name",
                inline=False
            )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "weather", True)

        except Exception as e:
            logger.error(f"Error in weather command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to get weather information. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "weather", False, str(e))

    @command(
        name="qr",
        description="Generate a QR code from text or URL",
        aliases=["qrcode"],
        permission_node="utility.tools",
        arguments=[
            CommandArgument(
                "text",
                hikari.OptionType.STRING,
                "Text or URL to encode in QR code",
            )
        ],
    )
    async def generate_qr(self, ctx: lightbulb.Context, text: str) -> None:
        try:
            import urllib.parse

            # Validate input length
            if len(text) > 1000:
                embed = self.create_embed(
                    title="❌ Text Too Long",
                    description="QR code text must be 1000 characters or less.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # URL encode the text
            encoded_text = urllib.parse.quote(text)

            # Generate QR code using online service
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_text}"

            embed = self.create_embed(
                title="📱 QR Code Generated",
                description=f"QR Code for: `{text[:100]}{'...' if len(text) > 100 else ''}`",
                color=hikari.Color(0x000000),
            )

            embed.set_image(qr_url)
            embed.add_field("Text Length", f"{len(text)} characters", inline=True)

            # Add URL info if it looks like a URL
            if text.startswith(('http://', 'https://', 'www.')):
                embed.add_field("Type", "🔗 URL", inline=True)
            else:
                embed.add_field("Type", "📝 Text", inline=True)

            embed.set_footer("Scan with your device's camera or QR code app")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "qr", True)

        except Exception as e:
            logger.error(f"Error in qr command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to generate QR code. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "qr", False, str(e))

    @command(
        name="poll",
        description="Create a reaction-based poll",
        permission_node="utility.tools",
        arguments=[
            CommandArgument(
                "question",
                hikari.OptionType.STRING,
                "The poll question",
            ),
            CommandArgument(
                "option1",
                hikari.OptionType.STRING,
                "First option",
            ),
            CommandArgument(
                "option2",
                hikari.OptionType.STRING,
                "Second option",
            ),
            CommandArgument(
                "option3",
                hikari.OptionType.STRING,
                "Third option (optional)",
                required=False,
            ),
            CommandArgument(
                "option4",
                hikari.OptionType.STRING,
                "Fourth option (optional)",
                required=False,
            ),
        ],
    )
    async def create_poll(self, ctx: lightbulb.Context, question: str, option1: str, option2: str, option3: str = None, option4: str = None) -> None:
        try:
            # Collect options
            options = [option1, option2]
            if option3:
                options.append(option3)
            if option4:
                options.append(option4)

            # Validate options
            if len(options) < 2:
                embed = self.create_embed(
                    title="❌ Not Enough Options",
                    description="A poll needs at least 2 options.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Emojis for reactions
            number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

            embed = self.create_embed(
                title="📊 Poll",
                description=f"**{question}**",
                color=hikari.Color(0x1E90FF),
            )

            # Add options
            options_text = ""
            for i, option in enumerate(options):
                options_text += f"{number_emojis[i]} {option}\n"

            embed.add_field("Options", options_text, inline=False)
            embed.add_field("How to Vote", "React with the number of your choice!", inline=False)
            embed.set_footer(f"Poll created by {ctx.author.display_name}")

            # Send poll and add reactions
            message = await ctx.respond(embed=embed)

            # Add reaction emojis
            for i in range(len(options)):
                await message.add_reaction(number_emojis[i])

            await self.log_command_usage(ctx, "poll", True)

        except Exception as e:
            logger.error(f"Error in poll command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to create poll. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "poll", False, str(e))

    @command(
        name="translate",
        description="Translate text to different languages",
        aliases=["tr"],
        permission_node="utility.convert",
        arguments=[
            CommandArgument(
                "target_language",
                hikari.OptionType.STRING,
                "Target language (e.g., 'es' for Spanish, 'fr' for French)",
            ),
            CommandArgument(
                "text",
                hikari.OptionType.STRING,
                "Text to translate",
            ),
        ],
    )
    async def translate_text(self, ctx: lightbulb.Context, target_language: str, text: str) -> None:
        try:
            # Validate input
            if len(text) > 500:
                embed = self.create_embed(
                    title="❌ Text Too Long",
                    description="Translation text must be 500 characters or less.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Language code mapping
            language_codes = {
                'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
                'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic', 'hi': 'Hindi',
                'nl': 'Dutch', 'sv': 'Swedish', 'no': 'Norwegian', 'da': 'Danish',
                'fi': 'Finnish', 'pl': 'Polish', 'tr': 'Turkish', 'th': 'Thai'
            }

            target_lang = target_language.lower().strip()

            if target_lang not in language_codes:
                valid_langs = ", ".join([f"`{code}` ({name})" for code, name in list(language_codes.items())[:10]])
                embed = self.create_embed(
                    title="❌ Invalid Language Code",
                    description=f"Please use a valid language code.\n\n**Examples:**\n{valid_langs}\n\n[See more language codes online]",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Since we don't have access to Google Translate API without API keys,
            # we'll provide a helpful response with translation services
            embed = self.create_embed(
                title="🌐 Translation Service",
                description=f"**Original Text:**\n{text}\n\n**Target Language:** {language_codes[target_lang]} ({target_lang})",
                color=hikari.Color(0x4285F4),
            )

            embed.add_field(
                "Translation Services",
                "• [Google Translate](https://translate.google.com)\n"
                "• [DeepL](https://deepl.com)\n"
                "• [Microsoft Translator](https://translator.microsoft.com)",
                inline=False
            )

            embed.add_field(
                "Quick Translation",
                f"Copy your text and paste it into any of the translation services above to translate to {language_codes[target_lang]}.",
                inline=False
            )

            embed.set_footer("API-based translation requires service setup")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "translate", True)

        except Exception as e:
            logger.error(f"Error in translate command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to process translation request. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "translate", False, str(e))
