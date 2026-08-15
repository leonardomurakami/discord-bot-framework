"""FastAPI routes for the fun plugin's web panel."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from ..config import (
    API_ENDPOINTS,
    DEFAULT_FACTS,
    DEFAULT_JOKES,
    DEFAULT_QUOTES,
    DEFAULT_WYR_QUESTIONS,
    DICE_LIMITS,
    RANDOM_NUMBER_LIMIT,
)

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from ..plugin import FunPlugin


def register_fun_routes(app: FastAPI, plugin: FunPlugin) -> None:
    """Register FastAPI routes for the fun plugin web panel."""

    @app.get("/plugin/fun", response_class=HTMLResponse)
    async def fun_panel(request: Request) -> HTMLResponse:
        return plugin.render_plugin_template(request, "panel.html")

    @app.post("/plugin/fun/api/roll")
    async def api_roll_dice(request: Request) -> HTMLResponse:
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

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.post("/plugin/fun/api/coinflip")
    async def api_coinflip(request: Request) -> HTMLResponse:
        try:
            result = random.choice(["Heads", "Tails"])
            return HTMLResponse(f"🪙 <strong>The coin landed on {result}!</strong>")
        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.post("/plugin/fun/api/8ball")
    async def api_8ball(request: Request) -> HTMLResponse:
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

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.post("/plugin/fun/api/random")
    async def api_random_number(request: Request) -> HTMLResponse:
        try:
            form_data = await request.form()
            min_val = int(form_data.get("min", 1))
            max_val = int(form_data.get("max", 100))

            if min_val > max_val:
                return HTMLResponse("❌ <strong>Invalid Range</strong><br>Minimum cannot be greater than maximum")

            if abs(max_val - min_val) > RANDOM_NUMBER_LIMIT:
                return HTMLResponse("❌ <strong>Range Too Large</strong><br>Range cannot exceed " f"{RANDOM_NUMBER_LIMIT:,} numbers")

            result = random.randint(min_val, max_val)
            total_possibilities = max_val - min_val + 1

            return HTMLResponse(
                f"🎯 <strong>Generated:</strong> {result}<br><strong>Range:</strong> {min_val} - {max_val}<br>"
                f"<strong>Possibilities:</strong> {total_possibilities:,}"
            )

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.post("/plugin/fun/api/joke")
    async def api_joke(request: Request) -> HTMLResponse:
        try:
            if plugin.session:
                try:
                    async with plugin.session.get(API_ENDPOINTS["joke"]) as resp:
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

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.post("/plugin/fun/api/quote")
    async def api_quote(request: Request) -> HTMLResponse:
        try:
            if plugin.session:
                try:
                    async with plugin.session.get(API_ENDPOINTS["quote"]) as resp:
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

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.get("/plugin/fun/api/wyr")
    async def api_wyr(request: Request) -> HTMLResponse:
        try:
            option_a, option_b = random.choice(DEFAULT_WYR_QUESTIONS)

            html_fragment = (
                f'<div class="wyr-options">'
                f'<div class="wyr-option"><strong>🅰️ Option A:</strong> {option_a}</div>'
                f'<div class="wyr-option"><strong>🅱️ Option B:</strong> {option_b}</div>'
                f"</div>"
                f'<div class="wyr-vote-buttons">'
                f'<button type="button" class="btn btn-wyr-a" onclick="wyrVote(\'a\')">🅰️ Vote A</button>'
                f'<button type="button" class="btn btn-wyr-b" onclick="wyrVote(\'b\')">🅱️ Vote B</button>'
                f"</div>"
                f'<div class="wyr-results" id="wyr-results">'
                f'<div class="wyr-bar-container">'
                f'<div class="wyr-bar-label">A: <span id="wyr-count-a">0</span> votes (<span id="wyr-pct-a">0.0</span>%)</div>'
                f'<div class="wyr-bar"><div class="wyr-bar-fill wyr-bar-a" id="wyr-bar-a" style="width:0%"></div></div>'
                f"</div>"
                f'<div class="wyr-bar-container">'
                f'<div class="wyr-bar-label">B: <span id="wyr-count-b">0</span> votes (<span id="wyr-pct-b">0.0</span>%)</div>'
                f'<div class="wyr-bar"><div class="wyr-bar-fill wyr-bar-b" id="wyr-bar-b" style="width:0%"></div></div>'
                f"</div>"
                f'<div class="wyr-total">Total votes: <span id="wyr-total">0</span></div>'
                f"</div>"
                f'<div class="card-actions">'
                f'<button class="btn" hx-get="/plugin/fun/api/wyr" hx-target="#wyr-result" hx-indicator="#wyr-loading">'
                f'<i class="fa-solid fa-rotate icon icon-sm" aria-hidden="true"></i>'
                f"<span>New question</span>"
                f"</button>"
                f'<span id="wyr-loading" class="htmx-indicator">Loading...</span>'
                f"</div>"
            )
            return HTMLResponse(html_fragment)

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.post("/plugin/fun/api/meme")
    async def api_meme(request: Request) -> HTMLResponse:
        try:
            if not plugin.session:
                return HTMLResponse("❌ <strong>Service Unavailable</strong><br>Meme service is currently unavailable.")

            try:
                async with plugin.session.get(API_ENDPOINTS["meme_primary"]) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if not data.get("nsfw", True):
                            title = data.get("title", "Random Meme")
                            subreddit = data.get("subreddit", "unknown")
                            ups = data.get("ups", 0)
                            img_url = data.get("url", "")
                            return HTMLResponse(
                                f"😂 <strong>{title}</strong><br>"
                                f'<img src="{img_url}" alt="{title}" class="meme-img"><br>'
                                f"<small>r/{subreddit} • 👍 {ups} upvotes</small>"
                            )
                        raise Exception("NSFW meme, trying different source")
            except Exception:
                pass

            try:
                async with plugin.session.get(API_ENDPOINTS["meme_secondary"]) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success") and data.get("data", {}).get("memes"):
                            meme = random.choice(data["data"]["memes"])
                            name = meme.get("name", "Random Meme")
                            img_url = meme.get("url", "")
                            return HTMLResponse(
                                f"😂 <strong>{name}</strong><br>"
                                f'<img src="{img_url}" alt="{name}" class="meme-img"><br>'
                                f"<small>Powered by Imgflip</small>"
                            )
            except Exception:
                pass

            return HTMLResponse("😅 <strong>Meme gods are taking a break!</strong><br>Couldn't fetch a meme right now.")

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.post("/plugin/fun/api/fact")
    async def api_fact(request: Request) -> HTMLResponse:
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

            return HTMLResponse(f"🤓 <strong>Random Fact:</strong><br><br>{fact_text}")

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")

    @app.post("/plugin/fun/api/choose")
    async def api_choose(request: Request) -> HTMLResponse:
        try:
            form_data = await request.form()
            option1 = (form_data.get("option1", "") or "").strip()
            option2 = (form_data.get("option2", "") or "").strip()

            if not option1 or not option2:
                return HTMLResponse("❌ <strong>Please provide both options!</strong>")

            chosen = random.choice([option1, option2])

            return HTMLResponse(
                f"🤔 <strong>I choose: {chosen}</strong><br><br>" f"<strong>Options:</strong><br>• {option1}<br>• {option2}"
            )

        except Exception as exc:  # pragma: no cover - FastAPI handles error paths
            return HTMLResponse(f"❌ <strong>Error:</strong> {exc}")
