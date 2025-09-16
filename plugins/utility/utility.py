import logging
import re
from datetime import datetime
import hikari
import lightbulb
import aiohttp
import base64
import hashlib

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

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
            CommandArgument("user", hikari.OptionType.USER, "User to get information about", required=False)
        ]
    )
    async def user_info(self, ctx: lightbulb.Context, user: hikari.User = None) -> None:
        try:
            target_user = user or ctx.author
            guild = ctx.get_guild()

            embed = self.create_embed(
                title=f"👤 {target_user.username}",
                color=hikari.Color(0x5865F2)
            )

            # Basic user info
            embed.add_field("User ID", str(target_user.id), inline=True)
            embed.add_field("Display Name", target_user.display_name, inline=True)
            embed.add_field("Bot Account", "Yes" if target_user.is_bot else "No", inline=True)

            # Account creation
            embed.add_field("Account Created", f"<t:{int(target_user.created_at.timestamp())}:R>", inline=True)

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
                    except (hikari.NotFoundError, hikari.ForbiddenError, AttributeError):
                        pass

                    if member:
                        # Join date
                        if member.joined_at:
                            embed.add_field("Joined Server", f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)

                        # Roles
                        roles = [f"<@&{role_id}>" for role_id in member.role_ids if role_id != guild.id]
                        if roles:
                            roles_text = " ".join(roles[:10])  # Limit to 10 roles
                            if len(roles) > 10:
                                roles_text += f" (+{len(roles) - 10} more)"
                            embed.add_field("Roles", roles_text, inline=False)

                        # Guild permissions
                        permissions = member.permissions
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
                    pass  # Not a member or can't get member info

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "userinfo", True)

        except Exception as e:
            logger.error(f"Error in userinfo command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to get user information: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "userinfo", False, str(e))

    @command(
        name="avatar",
        description="Get a user's avatar in high resolution",
        aliases=["av", "pfp"],
        permission_node="utility.info",
        arguments=[
            CommandArgument("user", hikari.OptionType.USER, "User to get avatar of", required=False)
        ]
    )
    async def avatar(self, ctx: lightbulb.Context, user: hikari.User = None) -> None:
        try:
            target_user = user or ctx.author

            embed = self.create_embed(
                title=f"🖼️ {target_user.display_name}'s Avatar",
                color=hikari.Color(0x9932CC)
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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "avatar", False, str(e))

    @command(
        name="timestamp",
        description="Convert time to Discord timestamp formats",
        aliases=["time", "ts"],
        permission_node="utility.convert",
        arguments=[
            CommandArgument("time_input", hikari.OptionType.STRING, "Time input (YYYY-MM-DD HH:MM, Unix timestamp, or 'now')", required=False, default="now")
        ]
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
                        "%m/%d/%Y"
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
                        color=hikari.Color(0xFF0000)
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

            # Create embed with all timestamp formats
            embed = self.create_embed(
                title="🕒 Discord Timestamps",
                description=f"Timestamp: `{timestamp}`",
                color=hikari.Color(0x00CED1)
            )

            formats = {
                "Default": f"<t:{timestamp}>",
                "Short Time": f"<t:{timestamp}:t>",
                "Long Time": f"<t:{timestamp}:T>",
                "Short Date": f"<t:{timestamp}:d>",
                "Long Date": f"<t:{timestamp}:D>",
                "Short Date/Time": f"<t:{timestamp}:f>",
                "Long Date/Time": f"<t:{timestamp}:F>",
                "Relative": f"<t:{timestamp}:R>"
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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "timestamp", False, str(e))

    @command(
        name="color",
        description="Display information about a color",
        aliases=["colour"],
        permission_node="utility.tools",
        arguments=[
            CommandArgument("color_input", hikari.OptionType.STRING, "Hex code (#FF0000) or color name (red)")
        ]
    )
    async def color_info(self, ctx: lightbulb.Context, color_input: str) -> None:
        try:
            # Clean input
            color_input = color_input.strip().lower()

            # Color name mappings
            color_names = {
                "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
                "yellow": "#FFFF00", "cyan": "#00FFFF", "magenta": "#FF00FF",
                "black": "#000000", "white": "#FFFFFF", "gray": "#808080",
                "orange": "#FFA500", "purple": "#800080", "pink": "#FFC0CB",
                "brown": "#A52A2A", "gold": "#FFD700", "silver": "#C0C0C0",
                "discord": "#5865F2", "blurple": "#5865F2"
            }

            # Parse color
            hex_color = None
            if color_input.startswith('#'):
                hex_color = color_input
            elif color_input in color_names:
                hex_color = color_names[color_input]
            else:
                embed = self.create_embed(
                    title="❌ Invalid Color",
                    description="Please provide a hex code (#FF0000) or color name (red, blue, etc.)",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Validate hex format
            if not re.match(r'^#[0-9A-Fa-f]{6}$', hex_color):
                embed = self.create_embed(
                    title="❌ Invalid Hex Code",
                    description="Hex code must be in format #RRGGBB (e.g., #FF0000)",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Convert to RGB
            hex_clean = hex_color.lstrip('#')
            rgb = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))

            # Convert to other formats
            rgb_str = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
            hsl = self._rgb_to_hsl(*rgb)
            hsl_str = f"hsl({hsl[0]}°, {hsl[1]}%, {hsl[2]}%)"

            # Create color integer for embed
            color_int = int(hex_clean, 16)

            embed = self.create_embed(
                title=f"🎨 Color: {hex_color.upper()}",
                color=hikari.Color(color_int)
            )

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
                color=hikari.Color(0xFF0000)
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
            CommandArgument("text", hikari.OptionType.STRING, "Text to encode/decode")
        ]
    )
    async def base64_convert(self, ctx: lightbulb.Context, action: str, text: str) -> None:
        try:
            action = action.lower().strip()

            if action not in ["encode", "decode", "enc", "dec"]:
                embed = self.create_embed(
                    title="❌ Invalid Action",
                    description="Action must be 'encode' or 'decode'",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if action in ["encode", "enc"]:
                # Encode to base64
                encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
                result = encoded
                action_text = "Encoded"
            else:
                # Decode from base64
                try:
                    decoded = base64.b64decode(text).decode('utf-8')
                    result = decoded
                    action_text = "Decoded"
                except Exception:
                    embed = self.create_embed(
                        title="❌ Invalid Base64",
                        description="The provided text is not valid base64.",
                        color=hikari.Color(0xFF0000)
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

            # Limit output length for display
            if len(result) > 1024:
                display_result = result[:1021] + "..."
            else:
                display_result = result

            embed = self.create_embed(
                title=f"🔢 Base64 {action_text}",
                color=hikari.Color(0x9932CC)
            )

            embed.add_field("Input", f"```\n{text[:500]}{'...' if len(text) > 500 else ''}\n```", inline=False)
            embed.add_field("Output", f"```\n{display_result}\n```", inline=False)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "base64", True)

        except Exception as e:
            logger.error(f"Error in base64 command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"Failed to process base64: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "base64", False, str(e))

    @command(
        name="hash",
        description="Generate hash of text (MD5, SHA1, SHA256)",
        permission_node="utility.tools",
        arguments=[
            CommandArgument("algorithm", hikari.OptionType.STRING, "Hash algorithm (md5, sha1, sha256)"),
            CommandArgument("text", hikari.OptionType.STRING, "Text to hash")
        ]
    )
    async def hash_text(self, ctx: lightbulb.Context, algorithm: str, text: str) -> None:
        try:
            algorithm = algorithm.lower().strip()

            if algorithm not in ["md5", "sha1", "sha256"]:
                embed = self.create_embed(
                    title="❌ Invalid Algorithm",
                    description="Algorithm must be 'md5', 'sha1', or 'sha256'",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Generate hash
            if algorithm == "md5":
                hash_obj = hashlib.md5(text.encode('utf-8'))
            elif algorithm == "sha1":
                hash_obj = hashlib.sha1(text.encode('utf-8'))
            elif algorithm == "sha256":
                hash_obj = hashlib.sha256(text.encode('utf-8'))

            result = hash_obj.hexdigest()

            embed = self.create_embed(
                title=f"🔐 {algorithm.upper()} Hash",
                color=hikari.Color(0x8B4513)
            )

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
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "hash", False, str(e))

    def _rgb_to_hsl(self, r: int, g: int, b: int) -> tuple:
        """Convert RGB to HSL color space."""
        r, g, b = r/255.0, g/255.0, b/255.0
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val

        # Lightness
        l = (max_val + min_val) / 2

        if diff == 0:
            h = s = 0  # Achromatic
        else:
            # Saturation
            s = diff / (2 - max_val - min_val) if l > 0.5 else diff / (max_val + min_val)

            # Hue
            if max_val == r:
                h = (g - b) / diff + (6 if g < b else 0)
            elif max_val == g:
                h = (b - r) / diff + 2
            elif max_val == b:
                h = (r - g) / diff + 4
            h /= 6

        return (int(h * 360), int(s * 100), int(l * 100))