from __future__ import annotations

import logging
from typing import Any

import aiohttp
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from bot.plugins.base import BasePlugin
from bot.web.mixins import WebPanelMixin

from .commands import setup_basic_commands, setup_content_commands, setup_game_commands
from .config import (
    API_ENDPOINTS,
    DEFAULT_JOKES,
    DEFAULT_QUOTES,
    DICE_LIMITS,
    RANDOM_NUMBER_LIMIT,
)

logger = logging.getLogger(__name__)


class FunPlugin(BasePlugin, WebPanelMixin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self.session: aiohttp.ClientSession | None = None
        self._register_commands()

    async def on_load(self) -> None:
        self.session = aiohttp.ClientSession()
        await super().on_load()

    async def on_unload(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
        await super().on_unload()

    def _register_commands(self) -> None:
        commands = setup_basic_commands(self) + setup_game_commands(self) + setup_content_commands(self)

        for command_func in commands:
            setattr(self, command_func.__name__, command_func)

    # Web Panel Implementation
    def get_panel_info(self) -> dict[str, Any]:
        """Return metadata about this plugin's web panel."""
        return {
            "name": "Fun & Games",
            "description": "Interactive fun commands and games panel",
            "route": "/plugin/fun",
            "icon": "🎮",
            "nav_order": 10,
        }

    def register_web_routes(self, app: FastAPI) -> None:
        """Register web routes for the fun plugin."""

        @app.get("/plugin/fun", response_class=HTMLResponse)
        async def fun_panel(request: Request):
            return self.render_plugin_template(request, "panel.html")

        @app.post("/plugin/fun/api/roll")
        async def api_roll_dice(request: Request):
            import random

            try:
                form_data = await request.form()
                dice = form_data.get("dice", "1d6")

                if "d" not in dice.lower():
                    return HTMLResponse("❌ <strong>Invalid Format</strong><br>Please use dice notation like 1d6, 2d20, etc.")

                parts = dice.lower().split("d")
                if len(parts) != 2:
                    return HTMLResponse("❌ <strong>Invalid Format</strong><br>Please use dice notation like 1d6, 2d20, etc.")

                num_dice = int(parts[0]) if parts[0] else 1
                num_sides = int(parts[1])

                if not (DICE_LIMITS["min_dice"] <= num_dice <= DICE_LIMITS["max_dice"]) or not (
                    DICE_LIMITS["min_sides"] <= num_sides <= DICE_LIMITS["max_sides"]
                ):
                    return HTMLResponse(
                        "❌ <strong>Invalid Range</strong><br>"
                        f"Dice: {DICE_LIMITS['min_dice']}-{DICE_LIMITS['max_dice']}, "
                        f"Sides: {DICE_LIMITS['min_sides']}-{DICE_LIMITS['max_sides']}"
                    )

                rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
                total = sum(rolls)

                if num_dice == 1:
                    result = f"🎲 <strong>You rolled a {total}!</strong>"
                else:
                    rolls_text = ", ".join(str(roll) for roll in rolls)
                    result = f"🎲 <strong>Rolls:</strong> {rolls_text}<br><strong>Total:</strong> {total}"

                return HTMLResponse(result)

            except Exception as exc:
                return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

        @app.post("/plugin/fun/api/coinflip")
        async def api_coinflip(request: Request):
            import random

            try:
                result = random.choice(["Heads", "Tails"])
                return HTMLResponse(f"🪙 <strong>The coin landed on {result}!</strong>")
            except Exception as exc:
                return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

        @app.post("/plugin/fun/api/8ball")
        async def api_8ball(request: Request):
            import random

            try:
                form_data = await request.form()
                question = form_data.get("question", "").strip()

                if not question:
                    return HTMLResponse("❌ <strong>Please ask a question!</strong>")

                responses = [
                    "It is certain",
                    "It is decidedly so",
                    "Without a doubt",
                    "Yes definitely",
                    "You may rely on it",
                    "As I see it, yes",
                    "Most likely",
                    "Outlook good",
                    "Yes",
                    "Signs point to yes",
                    "Reply hazy, try again",
                    "Ask again later",
                    "Better not tell you now",
                    "Cannot predict now",
                    "Concentrate and ask again",
                    "Don't count on it",
                    "My reply is no",
                    "My sources say no",
                    "Outlook not so good",
                    "Very doubtful",
                ]

                response = random.choice(responses)
                return HTMLResponse(f"🎱 <strong>Question:</strong> {question}<br><strong>Answer:</strong> {response}")

            except Exception as exc:
                return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

        @app.post("/plugin/fun/api/random")
        async def api_random_number(request: Request):
            import random

            try:
                form_data = await request.form()
                min_val = int(form_data.get("min", 1))
                max_val = int(form_data.get("max", 100))

                if min_val > max_val:
                    return HTMLResponse("❌ <strong>Invalid Range</strong><br>Minimum cannot be greater than maximum")

                if abs(max_val - min_val) > RANDOM_NUMBER_LIMIT:
                    return HTMLResponse(
                        "❌ <strong>Range Too Large</strong><br>Range cannot exceed " f"{RANDOM_NUMBER_LIMIT:,} numbers"
                    )

                result = random.randint(min_val, max_val)
                total_possibilities = max_val - min_val + 1

                return HTMLResponse(
                    f"🎯 <strong>Generated:</strong> {result}<br><strong>Range:</strong> {min_val} - {max_val}<br>"
                    f"<strong>Possibilities:</strong> {total_possibilities:,}"
                )

            except Exception as exc:
                return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

        @app.post("/plugin/fun/api/joke")
        async def api_joke(request: Request):
            import random

            try:
                if self.session:
                    try:
                        async with self.session.get(API_ENDPOINTS["joke"]) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data["type"] == "single":
                                    joke_text = data["joke"]
                                else:
                                    joke_text = f"{data['setup']}<br><br>{data['delivery']}"
                                return HTMLResponse(f"😂 <strong>Here's a joke for you:</strong><br><br>{joke_text}")
                    except Exception:
                        pass

                joke = random.choice(DEFAULT_JOKES)
                return HTMLResponse(f"😂 <strong>Here's a joke for you:</strong><br><br>{joke}")

            except Exception as exc:
                return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

        @app.post("/plugin/fun/api/quote")
        async def api_quote(request: Request):
            import random

            try:
                if self.session:
                    try:
                        async with self.session.get(API_ENDPOINTS["quote"]) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                quote_text = data.get("content")
                                quote_author = data.get("author")
                                if quote_text and quote_author:
                                    return HTMLResponse(
                                        f'💭 <strong>Inspirational Quote:</strong><br><br><em>"{quote_text}"</em><br><br>— {quote_author}'
                                    )
                    except Exception:
                        pass

                quote_text, quote_author = random.choice(DEFAULT_QUOTES)
                return HTMLResponse(f'💭 <strong>Inspirational Quote:</strong><br><br><em>"{quote_text}"</em><br><br>— {quote_author}')

            except Exception as exc:
                return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")
