import logging
import random
from typing import Dict, Any
import hikari
import lightbulb
import aiohttp

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

# Plugin metadata for the loader
PLUGIN_METADATA = {
    "name": "Fun",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Fun commands and games for entertainment including dice rolling, jokes, quotes, and random generators",
    "permissions": ["fun.games", "fun.images"],
}

logger = logging.getLogger(__name__)


class FunPlugin(BasePlugin):
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
        name="ping",
        description="Test command - check if bot is responding"
    )
    async def ping_command(self, ctx) -> None:
        try:
            logger.info(f"Ping command called by {ctx.author.username}")
            embed = self.create_embed(
                title="🏓 Pong!",
                description="Bot is working correctly!",
                color=hikari.Color(0x00FF00)
            )
            await ctx.respond(embed=embed)
            logger.info("Ping command responded successfully")
        except Exception as e:
            logger.error(f"Error in ping command: {e}")

    @command(
        name="roll",
        description="Roll dice (format: NdN, e.g., 2d6)",
        aliases=["r"],
        permission_node="fun.games",
        arguments=[
            CommandArgument("dice", hikari.OptionType.STRING, "Dice notation (e.g., 1d6, 2d20)", required=False, default="1d6")
        ]
    )
    async def roll_dice(self, ctx: lightbulb.Context, dice: str = "1d6") -> None:
        try:
            # Parse dice notation
            if 'd' not in dice.lower():
                embed = self.create_embed(
                    title="❌ Invalid Format",
                    description="Please use dice notation like `1d6`, `2d20`, etc.",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            parts = dice.lower().split('d')
            if len(parts) != 2:
                raise ValueError("Invalid dice format")

            num_dice = int(parts[0]) if parts[0] else 1
            num_sides = int(parts[1])

            if num_dice < 1 or num_dice > 20:
                embed = self.create_embed(
                    title="❌ Invalid Range",
                    description="Number of dice must be between 1 and 20.",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if num_sides < 2 or num_sides > 1000:
                embed = self.create_embed(
                    title="❌ Invalid Range",
                    description="Number of sides must be between 2 and 1000.",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Roll the dice
            rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
            total = sum(rolls)

            # Create result
            if num_dice == 1:
                result_text = f"🎲 You rolled a **{total}**!"
            else:
                rolls_text = ", ".join(str(roll) for roll in rolls)
                result_text = f"🎲 You rolled: {rolls_text}\nTotal: **{total}**"

            embed = self.create_embed(
                title=f"Dice Roll ({dice})",
                description=result_text,
                color=hikari.Color(0x00FF00)
            )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "roll", True)

        except ValueError:
            embed = self.create_embed(
                title="❌ Invalid Format",
                description="Please use valid dice notation like `1d6`, `2d20`, etc.",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "roll", False, "Invalid format")

        except Exception as e:
            logger.error(f"Error in roll command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "roll", False, str(e))


    @command(
        name="coinflip",
        description="Flip a coin",
        permission_node="fun.games"
    )
    async def flip_coin(self, ctx: lightbulb.Context) -> None:
        try:
            result = random.choice(["Heads", "Tails"])
            emoji = "🪙" if result == "Heads" else "🪙"

            embed = self.create_embed(
                title="Coin Flip",
                description=f"{emoji} The coin landed on **{result}**!",
                color=hikari.Color(0xFFD700)
            )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "coinflip", True)

        except Exception as e:
            logger.error(f"Error in coinflip command: {e}")
            await self.log_command_usage(ctx, "coinflip", False, str(e))

    @command(
        name="8ball",
        description="Ask the magic 8-ball a question",
        permission_node="fun.games",
        arguments=[
            CommandArgument("question", hikari.OptionType.STRING, "Your question for the 8-ball")
        ]
    )
    async def magic_8ball(self, ctx: lightbulb.Context, question: str) -> None:
        try:
            responses = [
                "It is certain", "It is decidedly so", "Without a doubt",
                "Yes definitely", "You may rely on it", "As I see it, yes",
                "Most likely", "Outlook good", "Yes", "Signs point to yes",
                "Reply hazy, try again", "Ask again later", "Better not tell you now",
                "Cannot predict now", "Concentrate and ask again",
                "Don't count on it", "My reply is no", "My sources say no",
                "Outlook not so good", "Very doubtful"
            ]

            response = random.choice(responses)

            embed = self.create_embed(
                title="🎱 Magic 8-Ball",
                description=f"**Question:** {question}\n**Answer:** {response}",
                color=hikari.Color(0x8B00FF)
            )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "8ball", True)

        except Exception as e:
            logger.error(f"Error in 8ball command: {e}")
            await self.log_command_usage(ctx, "8ball", False, str(e))

    @command(
        name="joke",
        description="Get a random joke"
    )
    async def random_joke(self, ctx: lightbulb.Context) -> None:
        try:
            if not self.session:
                embed = self.create_embed(
                    title="❌ Service Unavailable",
                    description="Joke service is currently unavailable.",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Try to fetch from joke API
            try:
                async with self.session.get("https://v2.jokeapi.dev/joke/Programming,Miscellaneous?blacklistFlags=nsfw,religious,political,racist,sexist,explicit") as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        if data["type"] == "single":
                            joke_text = data["joke"]
                        else:
                            joke_text = f"{data['setup']}\n\n{data['delivery']}"

                        embed = self.create_embed(
                            title="😂 Random Joke",
                            description=joke_text,
                            color=hikari.Color(0xFFD700)
                        )
                    else:
                        raise Exception("API request failed")

            except Exception:
                # Fallback to local jokes
                local_jokes = [
                    "Why don't scientists trust atoms? Because they make up everything!",
                    "Why did the scarecrow win an award? He was outstanding in his field!",
                    "Why don't eggs tell jokes? They'd crack each other up!",
                    "What do you call a fake noodle? An impasta!",
                    "Why did the math book look so sad? Because it was full of problems!",
                ]

                joke_text = random.choice(local_jokes)
                embed = self.create_embed(
                    title="😂 Random Joke",
                    description=joke_text,
                    color=hikari.Color(0xFFD700)
                )

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "joke", True)

        except Exception as e:
            logger.error(f"Error in joke command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to get a joke. Try again later!",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "joke", False, str(e))

    @command(
        name="choose",
        description="Let the bot choose between options",
        arguments=[
            CommandArgument("option1", hikari.OptionType.STRING, "Option 1"),
            CommandArgument("option2", hikari.OptionType.STRING, "Option 2"),
        ]
    )
    async def choose_option(self, ctx: lightbulb.Context, option1: str, option2: str) -> None:
        try:
            # Split and clean options
            choices = [option1, option2]

            if len(choices) < 2:
                embed = self.create_embed(
                    title="❌ Not Enough Options",
                    description="Please provide at least 2 options.",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            chosen = random.choice(choices)

            embed = self.create_embed(
                title="🤔 Choice Made",
                description=f"I choose: **{chosen}**",
                color=hikari.Color(0x00FF00)
            )

            # Add all options as a field
            options_text = "\n".join([f"• {choice}" for choice in choices])
            embed.add_field("Options", options_text, inline=False)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "choose", True)

        except Exception as e:
            logger.error(f"Error in choose command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "choose", False, str(e))

    @command(
        name="random",
        description="Generate random numbers within a range",
        aliases=["rng", "rand"],
        permission_node="fun.games",
        arguments=[
            CommandArgument("min_value", hikari.OptionType.INTEGER, "Minimum value (default: 1)", required=False, default=1),
            CommandArgument("max_value", hikari.OptionType.INTEGER, "Maximum value (default: 100)", required=False, default=100)
        ]
    )
    async def random_number(self, ctx: lightbulb.Context, min_value: int = 1, max_value: int = 100) -> None:
        try:
            # Validate input
            if min_value > max_value:
                embed = self.create_embed(
                    title="❌ Invalid Range",
                    description="Minimum value cannot be greater than maximum value.",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Prevent extremely large ranges
            if abs(max_value - min_value) > 10_000_000:
                embed = self.create_embed(
                    title="❌ Range Too Large",
                    description="Range cannot exceed 10 million numbers.",
                    color=hikari.Color(0xFF0000)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Generate random number
            result = random.randint(min_value, max_value)

            embed = self.create_embed(
                title="🎲 Random Number",
                description=f"🎯 Generated: **{result}**",
                color=hikari.Color(0x9932CC)
            )

            embed.add_field("Range", f"{min_value} - {max_value}", inline=True)
            embed.add_field("Total Possibilities", str(max_value - min_value + 1), inline=True)

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "random", True)

        except Exception as e:
            logger.error(f"Error in random command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "random", False, str(e))

    @command(
        name="quote",
        description="Get a random inspirational quote",
        aliases=["inspire", "wisdom"]
    )
    async def random_quote(self, ctx: lightbulb.Context) -> None:
        try:
            # Try to fetch from online API first
            quote_text = None
            quote_author = None

            if self.session:
                try:
                    async with self.session.get("https://api.quotable.io/random?maxLength=150") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            quote_text = data.get("content")
                            quote_author = data.get("author")
                except Exception:
                    pass  # Fall back to local quotes

            # Fallback to local quotes if API fails
            if not quote_text:
                local_quotes = [
                    ("The only way to do great work is to love what you do.", "Steve Jobs"),
                    ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
                    ("Life is what happens to you while you're busy making other plans.", "John Lennon"),
                    ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
                    ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
                    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
                    ("The only impossible journey is the one you never begin.", "Tony Robbins"),
                    ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
                    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
                    ("The only limit to our realization of tomorrow will be our doubts of today.", "Franklin D. Roosevelt"),
                    ("Do not go where the path may lead, go instead where there is no path and leave a trail.", "Ralph Waldo Emerson"),
                    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
                    ("Don't be afraid to give up the good to go for the great.", "John D. Rockefeller"),
                    ("If you really look closely, most overnight successes took a long time.", "Steve Jobs"),
                    ("The greatest glory in living lies not in never falling, but in rising every time we fall.", "Nelson Mandela")
                ]

                quote_text, quote_author = random.choice(local_quotes)

            embed = self.create_embed(
                title="💭 Inspirational Quote",
                description=f'*"{quote_text}"*',
                color=hikari.Color(0x8A2BE2)
            )

            if quote_author:
                embed.add_field("Author", f"— {quote_author}", inline=False)

            # Add a random motivational emoji
            motivational_emojis = ["💪", "🌟", "✨", "🎯", "🚀", "💎", "🔥", "⭐"]
            emoji = random.choice(motivational_emojis)
            embed.set_footer(f"{emoji} Stay inspired!")

            await ctx.respond(embed=embed)
            await self.log_command_usage(ctx, "quote", True)

        except Exception as e:
            logger.error(f"Error in quote command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description="Failed to get a quote. Try again later!",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "quote", False, str(e))