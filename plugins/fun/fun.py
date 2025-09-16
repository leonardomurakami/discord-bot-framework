import logging
import random
from typing import Dict, Any
import hikari
import lightbulb
import aiohttp

from bot.plugins.base import BasePlugin
from bot.plugins.commands import command, CommandArgument

logger = logging.getLogger(__name__)


class FunPlugin(BasePlugin):
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession = None

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Fun",
            "version": "1.0.0",
            "author": "Bot Framework",
            "description": "Fun commands and games for entertainment",
            "permissions": ["fun.games", "fun.images"],
        }

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