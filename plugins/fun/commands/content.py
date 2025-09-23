from __future__ import annotations

import logging
import random
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import hikari
import lightbulb

from bot.plugins.commands import command

from ..config import (
    API_ENDPOINTS,
    DEFAULT_FACTS,
    DEFAULT_JOKES,
    DEFAULT_QUOTES,
    EDUCATIONAL_EMOJIS,
    MOTIVATIONAL_EMOJIS,
)

if TYPE_CHECKING:
    from ..plugin import FunPlugin

logger = logging.getLogger(__name__)


def setup_content_commands(plugin: FunPlugin) -> list[Callable[..., Any]]:
    """Register commands that deliver jokes, quotes, memes, and facts."""

    @command(name="joke", description="Get a random joke")
    async def random_joke(ctx: lightbulb.Context) -> None:
        try:
            if not plugin.session:
                embed = plugin.create_embed(
                    title="❌ Service Unavailable",
                    description="Joke service is currently unavailable.",
                    color=hikari.Color(0xFF0000),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            try:
                async with plugin.session.get(API_ENDPOINTS["joke"]) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        if data["type"] == "single":
                            joke_text = data["joke"]
                        else:
                            joke_text = f"{data['setup']}\n\n{data['delivery']}"

                        embed = plugin.create_embed(
                            title="😂 Random Joke",
                            description=joke_text,
                            color=hikari.Color(0xFFD700),
                        )
                    else:
                        raise Exception("API request failed")

            except Exception:
                joke_text = random.choice(DEFAULT_JOKES)
                embed = plugin.create_embed(
                    title="😂 Random Joke",
                    description=joke_text,
                    color=hikari.Color(0xFFD700),
                )

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "joke", True)

        except Exception as exc:
            logger.error("Error in joke command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to get a joke. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "joke", False, str(exc))

    @command(
        name="quote",
        description="Get a random inspirational quote",
        aliases=["inspire", "wisdom"],
    )
    async def random_quote(ctx: lightbulb.Context) -> None:
        try:
            quote_text: str | None = None
            quote_author: str | None = None

            if plugin.session:
                try:
                    async with plugin.session.get(API_ENDPOINTS["quote"]) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            quote_text = data.get("content")
                            quote_author = data.get("author")
                except Exception:
                    pass

            if not quote_text:
                quote_text, quote_author = random.choice(DEFAULT_QUOTES)

            embed = plugin.create_embed(
                title="💭 Inspirational Quote",
                description=f'*"{quote_text}"*',
                color=hikari.Color(0x8A2BE2),
            )

            if quote_author:
                embed.add_field("Author", f"— {quote_author}", inline=False)

            emoji = random.choice(MOTIVATIONAL_EMOJIS)
            embed.set_footer(f"{emoji} Stay inspired!")

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "quote", True)

        except Exception as exc:
            logger.error("Error in quote command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to get a quote. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "quote", False, str(exc))

    @command(
        name="meme",
        description="Get a random meme",
        permission_node="basic.images",
    )
    async def random_meme(ctx: lightbulb.Context) -> None:
        try:
            if not plugin.session:
                embed = plugin.create_embed(
                    title="❌ Service Unavailable",
                    description="Meme service is currently unavailable.",
                    color=hikari.Color(0xFF0000),
                )
                await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            try:
                async with plugin.session.get(API_ENDPOINTS["meme_primary"]) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        if not data.get("nsfw", True):
                            embed = plugin.create_embed(
                                title=f"😂 {data.get('title', 'Random Meme')}",
                                color=hikari.Color(0xFF6B35),
                            )

                            embed.set_image(data.get("url"))
                            embed.add_field("Subreddit", f"r/{data.get('subreddit', 'unknown')}", inline=True)
                            embed.add_field("Upvotes", f"👍 {data.get('ups', 0)}", inline=True)

                            if data.get("postLink"):
                                embed.add_field("Source", f"[View on Reddit]({data['postLink']})", inline=False)

                            await ctx.respond(embed=embed)
                            await plugin.log_command_usage(ctx, "meme", True)
                            return
                        raise Exception("NSFW meme, trying different source")

            except Exception:
                try:
                    async with plugin.session.get(API_ENDPOINTS["meme_secondary"]) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("success") and data.get("data", {}).get("memes"):
                                meme = random.choice(data["data"]["memes"])

                                embed = plugin.create_embed(
                                    title=f"😂 {meme.get('name', 'Random Meme')}",
                                    color=hikari.Color(0xFF6B35),
                                )

                                embed.set_image(meme.get("url"))
                                embed.set_footer("Powered by Imgflip")

                                await ctx.respond(embed=embed)
                                await plugin.log_command_usage(ctx, "meme", True)
                                return
                except Exception:
                    pass

            embed = plugin.create_embed(
                title="😅 Meme Service Unavailable",
                description="Sorry, couldn't fetch a meme right now. The meme gods are taking a break!",
                color=hikari.Color(0xFFAA00),
            )
            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "meme", True)

        except Exception as exc:
            logger.error("Error in meme command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to get a meme. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "meme", False, str(exc))

    @command(
        name="fact",
        description="Get a random interesting fact",
        aliases=["randomfact"],
    )
    async def random_fact(ctx: lightbulb.Context) -> None:
        try:
            fact_text: str | None = None

            if plugin.session:
                try:
                    async with plugin.session.get(API_ENDPOINTS["fact"]) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            fact_text = data.get("text")
                except Exception:
                    pass

            if not fact_text:
                fact_text = random.choice(DEFAULT_FACTS)

            embed = plugin.create_embed(
                title="🤓 Random Fact",
                description=fact_text,
                color=hikari.Color(0x4169E1),
            )

            emoji = random.choice(EDUCATIONAL_EMOJIS)
            embed.set_footer(f"{emoji} The more you know!")

            await ctx.respond(embed=embed)
            await plugin.log_command_usage(ctx, "fact", True)

        except Exception as exc:
            logger.error("Error in fact command: %s", exc)
            embed = plugin.create_embed(
                title="❌ Error",
                description="Failed to get a fact. Try again later!",
                color=hikari.Color(0xFF0000),
            )
            await plugin.smart_respond(ctx, embed=embed, ephemeral=True)
            await plugin.log_command_usage(ctx, "fact", False, str(exc))

    return [random_joke, random_quote, random_meme, random_fact]
