from __future__ import annotations

import base64
import hashlib
import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import (
    BASE64_ACTIONS,
    BASE64_COLOR,
    COLOR_NAME_MAP,
    ERROR_COLOR,
    HASH_ALGORITHMS,
    HASH_COLOR,
    TIMESTAMP_COLOR,
    TRANSLATE_COLOR,
    TRANSLATE_LANGUAGE_CODES,
)
from ..utils import parse_timestamp_input, rgb_to_hsl

if TYPE_CHECKING:
    from ..plugin import UtilityPlugin

logger = logging.getLogger(__name__)


def setup_convert_commands(plugin: UtilityPlugin) -> list[Callable[..., Any]]:
    """Register conversion and formatting commands."""

    @command(
        name="timestamp",
        description="Convert time to Discord timestamp formats",
        aliases=["time", "ts"],
        permission_node="basic.utility.convert.use",
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
    async def timestamp(ctx: lightbulb.Context, time_input: str = "now") -> None:
        try:
            timestamp_value = parse_timestamp_input(time_input)

            embed = plugin.create_embed(
                title="🕒 Discord Timestamps",
                description=f"Timestamp: `{timestamp_value}`",
                color=TIMESTAMP_COLOR,
            )

            formats = {
                "Default": f"<t:{timestamp_value}>",
                "Short Time": f"<t:{timestamp_value}:t>",
                "Long Time": f"<t:{timestamp_value}:T>",
                "Short Date": f"<t:{timestamp_value}:d>",
                "Long Date": f"<t:{timestamp_value}:D>",
                "Short Date/Time": f"<t:{timestamp_value}:f>",
                "Long Date/Time": f"<t:{timestamp_value}:F>",
                "Relative": f"<t:{timestamp_value}:R>",
            }

            for name, formatted in formats.items():
                embed.add_field(name, f"`{formatted}`\n{formatted}", inline=True)

            embed.set_footer("Copy the format you want to use in your messages!")

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "timestamp", True)

        except ValueError:
            embed = plugin.create_embed(
                title="❌ Invalid Format",
                description=("Please use formats like:\n• `YYYY-MM-DD HH:MM`\n• `YYYY-MM-DD`\n" "• Unix timestamp\n• `now`"),
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "timestamp", False, "invalid format")

        except Exception as exc:
            logger.error("Error in timestamp command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to create timestamp: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "timestamp", False, str(exc))

    @command(
        name="color",
        description="Display information about a color",
        aliases=["colour"],
        permission_node="basic.utility.tools.use",
        arguments=[
            CommandArgument(
                "color_input",
                hikari.OptionType.STRING,
                "Hex code (#FF0000) or color name (red)",
            )
        ],
    )
    async def color_info(ctx: lightbulb.Context, color_input: str) -> None:
        try:
            cleaned_input = color_input.strip().lower()

            if cleaned_input.startswith("#"):
                hex_color = cleaned_input
            else:
                hex_color = COLOR_NAME_MAP.get(cleaned_input)

            if not hex_color:
                embed = plugin.create_embed(
                    title="❌ Invalid Color",
                    description="Please provide a hex code (#FF0000) or color name (red, blue, etc.)",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if not re.match(r"^#[0-9A-Fa-f]{6}$", hex_color):
                embed = plugin.create_embed(
                    title="❌ Invalid Hex Code",
                    description="Hex code must be in format #RRGGBB (e.g., #FF0000)",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            hex_clean = hex_color.lstrip("#")
            rgb = tuple(int(hex_clean[i : i + 2], 16) for i in (0, 2, 4))
            hsl = rgb_to_hsl(*rgb)

            color_int = int(hex_clean, 16)
            embed = plugin.create_embed(title=f"🎨 Color: {hex_color.upper()}", color=hikari.Color(color_int))

            embed.add_field("Hex", hex_color.upper(), inline=True)
            embed.add_field("RGB", f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})", inline=True)
            embed.add_field("HSL", f"hsl({hsl[0]}°, {hsl[1]}%, {hsl[2]}%)", inline=True)
            embed.add_field("Decimal", str(color_int), inline=True)
            preview_url = f"https://via.placeholder.com/300x100/{hex_clean}/{hex_clean}.png"
            embed.set_image(preview_url)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "color", True)

        except Exception as exc:
            logger.error("Error in color command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to process color: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "color", False, str(exc))

    @command(
        name="base64",
        description="Encode or decode base64 text",
        aliases=["b64"],
        permission_node="basic.utility.convert.use",
        arguments=[
            CommandArgument("action", hikari.OptionType.STRING, "encode or decode"),
            CommandArgument("text", hikari.OptionType.STRING, "Text to encode/decode"),
        ],
    )
    async def base64_convert(ctx: lightbulb.Context, action: str, text: str) -> None:
        try:
            normalised_action = action.lower().strip()

            if normalised_action not in BASE64_ACTIONS:
                embed = plugin.create_embed(
                    title="❌ Invalid Action",
                    description="Action must be 'encode' or 'decode'",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if normalised_action in {"encode", "enc"}:
                result = base64.b64encode(text.encode("utf-8")).decode("utf-8")
                action_text = "Encoded"
            else:
                try:
                    result = base64.b64decode(text).decode("utf-8")
                except Exception:
                    embed = plugin.create_embed(
                        title="❌ Invalid Base64",
                        description="The provided text is not valid base64.",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return
                action_text = "Decoded"

            display_result = result if len(result) <= 1024 else result[:1021] + "..."

            embed = plugin.create_embed(title=f"🔢 Base64 {action_text}", color=BASE64_COLOR)
            input_excerpt = text[:500] + ("..." if len(text) > 500 else "")
            embed.add_field("Input", f"```\n{input_excerpt}\n```", inline=False)
            embed.add_field("Output", f"```\n{display_result}\n```", inline=False)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "base64", True)

        except Exception as exc:
            logger.error("Error in base64 command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to process base64: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "base64", False, str(exc))

    @command(
        name="hash",
        description="Generate hash of text (MD5, SHA1, SHA256)",
        permission_node="basic.utility.tools.use",
        arguments=[
            CommandArgument(
                "algorithm",
                hikari.OptionType.STRING,
                "Hash algorithm (md5, sha1, sha256)",
            ),
            CommandArgument("text", hikari.OptionType.STRING, "Text to hash"),
        ],
    )
    async def hash_text(ctx: lightbulb.Context, algorithm: str, text: str) -> None:
        try:
            algorithm_key = algorithm.lower().strip()
            if algorithm_key not in HASH_ALGORITHMS:
                embed = plugin.create_embed(
                    title="❌ Invalid Algorithm",
                    description="Algorithm must be 'md5', 'sha1', or 'sha256'",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            hash_function = getattr(hashlib, HASH_ALGORITHMS[algorithm_key])
            result = hash_function(text.encode("utf-8")).hexdigest()

            embed = plugin.create_embed(title=f"🔐 {algorithm_key.upper()} Hash", color=HASH_COLOR)
            display_input = text[:100] + ("..." if len(text) > 100 else "")
            embed.add_field("Input", f"```\n{display_input}\n```", inline=False)
            embed.add_field("Hash", f"```\n{result}\n```", inline=False)
            embed.add_field("Algorithm", algorithm_key.upper(), inline=True)
            embed.add_field("Length", f"{len(result)} characters", inline=True)

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "hash", True)

        except Exception as exc:
            logger.error("Error in hash command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description=f"Failed to generate hash: {exc}",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "hash", False, str(exc))

    @command(
        name="translate",
        description="Translate text to different languages",
        aliases=["tr"],
        permission_node="basic.utility.convert.use",
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
    async def translate_text(ctx: lightbulb.Context, target_language: str, text: str) -> None:
        try:
            if len(text) > 500:
                embed = plugin.create_embed(
                    title="❌ Text Too Long",
                    description="Translation text must be 500 characters or less.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            target_lang = target_language.lower().strip()
            if target_lang not in TRANSLATE_LANGUAGE_CODES:
                examples = ", ".join(f"`{code}` ({name})" for code, name in list(TRANSLATE_LANGUAGE_CODES.items())[:10])
                embed = plugin.create_embed(
                    title="❌ Invalid Language Code",
                    description=(
                        "Please use a valid language code.\n\n**Examples:**\n" f"{examples}\n\n[See more language codes online]"
                    ),
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            embed = plugin.create_embed(
                title="🌐 Translation Service",
                description=(
                    f"**Original Text:**\n{text}\n\n" f"**Target Language:** {TRANSLATE_LANGUAGE_CODES[target_lang]} ({target_lang})"
                ),
                color=TRANSLATE_COLOR,
            )
            embed.add_field(
                "Translation Services",
                "• [Google Translate](https://translate.google.com)\n"
                "• [DeepL](https://deepl.com)\n"
                "• [Microsoft Translator](https://translator.microsoft.com)",
                inline=False,
            )
            embed.add_field(
                "Quick Translation",
                (
                    "Copy your text and paste it into any of the translation services above "
                    f"to translate to {TRANSLATE_LANGUAGE_CODES[target_lang]}."
                ),
                inline=False,
            )
            embed.set_footer("API-based translation requires service setup")

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "translate", True)

        except Exception as exc:
            logger.error("Error in translate command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to process translation request. Try again later!",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "translate", False, str(exc))

    return [timestamp, color_info, base64_convert, hash_text, translate_text]
