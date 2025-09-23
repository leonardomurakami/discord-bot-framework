from __future__ import annotations

import logging
import re
import urllib.parse
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..config import (
    ERROR_COLOR,
    POLL_COLOR,
    POLL_NUMBER_EMOJIS,
    QR_COLOR,
    QR_TEXT_LIMIT,
    REMINDER_COLOR,
)

if TYPE_CHECKING:
    from ..plugin import UtilityPlugin

logger = logging.getLogger(__name__)


def setup_tool_commands(plugin: UtilityPlugin) -> list[Callable[..., Any]]:
    """Register utility and productivity commands."""

    @command(
        name="onthisday",
        description="Show historical events for a date (timedelta or dd/mm/yyyy)",
        aliases=["otd", "history"],
        permission_node="basic.utility.tools.use",
        arguments=[
            CommandArgument(
                "date",
                hikari.OptionType.STRING,
                "Date as timedelta (5m, 1h, 20d) or dd/mm/yyyy format",
            ),
        ],
    )
    async def on_this_day(ctx: lightbulb.Context, date: str) -> None:
        try:
            # Parse input - either timedelta or dd/mm/yyyy format
            target_date = None

            # Try timedelta format first (e.g., "5m", "1h", "20d")
            timedelta_match = re.match(r"^(\d+)([mhd])$", date.lower().strip())
            if timedelta_match:
                amount = int(timedelta_match.group(1))
                unit = timedelta_match.group(2)

                if unit == "m":
                    delta = timedelta(minutes=amount)
                elif unit == "h":
                    delta = timedelta(hours=amount)
                else:  # unit == "d"
                    delta = timedelta(days=amount)

                target_date = datetime.now() + delta
            else:
                # Try dd/mm/yyyy format
                date_match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date.strip())
                if date_match:
                    day = int(date_match.group(1))
                    month = int(date_match.group(2))
                    year = int(date_match.group(3))

                    if not (1 <= day <= 31 and 1 <= month <= 12):
                        raise ValueError("Invalid date: day must be 1-31, month must be 1-12")

                    target_date = datetime(year, month, day)
                else:
                    embed = plugin.create_embed(
                        title="❌ Invalid Date Format",
                        description="Use format like: `5m`, `1h`, `20d` or `25/12/2024`",
                        color=ERROR_COLOR,
                    )
                    await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

            # Get historical events from Wikipedia API
            month = target_date.month
            day = target_date.day

            url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{month:02d}/{day:02d}"

            headers = {"User-Agent": "discord-bot-framework/1.0 (aiohttp; +https://github.com/discord-bot-framework) Bot"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Wikipedia API returned status {response.status}")

                    data = await response.json()

            # Create embed with historical events
            embed = plugin.create_embed(
                title=f"📅 On This Day - {target_date.strftime('%B %d')}",
                description=f"Historical events for {target_date.strftime('%B %d')}",
                color=REMINDER_COLOR,
            )

            # Add selected events (limit to avoid embed size limits)
            if "selected" in data and data["selected"]:
                events_text = ""
                for i, event in enumerate(data["selected"][:3]):  # Limit to 3 events
                    year = event.get("year", "Unknown")
                    text = event.get("text", "No description available")
                    # Clean up the text and limit length
                    clean_text = re.sub(r"<[^>]+>", "", text)[:150]
                    if len(text) > 150:
                        clean_text += "..."
                    events_text += f"**{year}**: {clean_text}\n\n"

                if events_text:
                    embed.add_field("🏛️ Historical Events", events_text.strip(), inline=False)

            # Add births if available
            if "births" in data and data["births"]:
                births_text = ""
                for i, birth in enumerate(data["births"][:2]):  # Limit to 2 births
                    year = birth.get("year", "Unknown")
                    text = birth.get("text", "No description available")
                    clean_text = re.sub(r"<[^>]+>", "", text)[:100]
                    if len(text) > 100:
                        clean_text += "..."
                    births_text += f"**{year}**: {clean_text}\n"

                if births_text:
                    embed.add_field("👶 Notable Births", births_text.strip(), inline=True)

            # Add deaths if available
            if "deaths" in data and data["deaths"]:
                deaths_text = ""
                for i, death in enumerate(data["deaths"][:2]):  # Limit to 2 deaths
                    year = death.get("year", "Unknown")
                    text = death.get("text", "No description available")
                    clean_text = re.sub(r"<[^>]+>", "", text)[:100]
                    if len(text) > 100:
                        clean_text += "..."
                    deaths_text += f"**{year}**: {clean_text}\n"

                if deaths_text:
                    embed.add_field("⚰️ Notable Deaths", deaths_text.strip(), inline=True)

            if target_date.date() != datetime.now().date():
                embed.add_field("📅 Date", f"<t:{int(target_date.timestamp())}:D>", inline=True)

            embed.set_footer("Data from Wikipedia • More events available on Wikipedia")

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "onthisday", True)

        except ValueError as exc:
            embed = plugin.create_embed(
                title="❌ Invalid Input",
                description=str(exc),
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "onthisday", False, str(exc))

        except Exception as exc:
            logger.error("Error in onthisday command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to fetch historical events. Try again later!",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "onthisday", False, str(exc))

    @command(
        name="qr",
        description="Generate a QR code from text or URL",
        aliases=["qrcode"],
        permission_node="basic.utility.tools.use",
        arguments=[
            CommandArgument(
                "text",
                hikari.OptionType.STRING,
                "Text or URL to encode in QR code",
            )
        ],
    )
    async def generate_qr(ctx: lightbulb.Context, text: str) -> None:
        try:
            if len(text) > QR_TEXT_LIMIT:
                embed = plugin.create_embed(
                    title="❌ Text Too Long",
                    description="QR code text must be 1000 characters or less.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            encoded_text = urllib.parse.quote(text)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_text}"

            embed = plugin.create_embed(
                title="📱 QR Code Generated",
                description=f"QR Code for: `{text[:100]}{'...' if len(text) > 100 else ''}`",
                color=QR_COLOR,
            )
            embed.set_image(qr_url)
            embed.add_field("Text Length", f"{len(text)} characters", inline=True)
            embed.add_field(
                "Type",
                "🔗 URL" if text.startswith(("http://", "https://", "www.")) else "📝 Text",
                inline=True,
            )
            embed.set_footer("Scan with your device's camera or QR code app")

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "qr", True)

        except Exception as exc:
            logger.error("Error in qr command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to generate QR code. Try again later!",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "qr", False, str(exc))

    @command(
        name="poll",
        description="Create a reaction-based poll",
        permission_node="basic.utility.tools.use",
        arguments=[
            CommandArgument("question", hikari.OptionType.STRING, "The poll question"),
            CommandArgument("option1", hikari.OptionType.STRING, "First option"),
            CommandArgument("option2", hikari.OptionType.STRING, "Second option"),
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
    async def create_poll(
        ctx: lightbulb.Context,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
    ) -> None:
        try:
            options = [option1, option2]
            if option3:
                options.append(option3)
            if option4:
                options.append(option4)

            if len(options) < 2:
                embed = plugin.create_embed(
                    title="❌ Not Enough Options",
                    description="A poll needs at least 2 options.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if len(options) > len(POLL_NUMBER_EMOJIS):
                embed = plugin.create_embed(
                    title="❌ Too Many Options",
                    description="Polls can have up to 4 options.",
                    color=ERROR_COLOR,
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            embed = plugin.create_embed(title="📊 Poll", description=f"**{question}**", color=POLL_COLOR)
            options_text = "\n".join(f"{POLL_NUMBER_EMOJIS[i]} {option}" for i, option in enumerate(options))
            embed.add_field("Options", options_text, inline=False)
            embed.add_field("How to Vote", "React with the number of your choice!", inline=False)
            embed.set_footer(f"Poll created by {ctx.author.display_name}")

            message = await ctx.respond(embed=embed)
            for i in range(len(options)):
                await message.add_reaction(POLL_NUMBER_EMOJIS[i])

            await plugin.log_command_usage(ctx, "poll", True)

        except Exception as exc:
            logger.error("Error in poll command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to create poll. Try again later!",
                color=ERROR_COLOR,
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "poll", False, str(exc))

    return [on_this_day, generate_qr, create_poll]
