"""FastAPI routes for the games plugin web panel."""

from __future__ import annotations

import html
import logging
import random
import time
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response

from ..config import (
    ANGLE_ACHIEVEMENTS,
    ANGLE_MAX_ATTEMPTS,
    DIFFICULTY_EMOJIS,
    RPS_ACHIEVEMENTS,
    TRIVIA_ACHIEVEMENTS,
    TRIVIA_CATEGORIES,
    TRIVIA_DIFFICULTIES,
    games_settings,
)
from ..utils.angle_image import generate_angle_image

if TYPE_CHECKING:
    from ..plugin import GamesPlugin

logger = logging.getLogger(__name__)

# In-memory trivia session state: (user_id, guild_id) → start_timestamp
_trivia_sessions: dict[tuple[int, int], float] = {}

# RPS choices and outcome logic (mirrors views/rps.py)
_RPS_CHOICES = {
    "rock": {"emoji": "🪨", "label": "Rock", "beats": "scissors"},
    "paper": {"emoji": "📄", "label": "Paper", "beats": "rock"},
    "scissors": {"emoji": "✂️", "label": "Scissors", "beats": "paper"},
}


def _rps_determine_result(player: str, bot_choice: str) -> str:
    """Return 'win', 'lose', or 'draw'."""
    if player == bot_choice:
        return "draw"
    if _RPS_CHOICES[player]["beats"] == bot_choice:
        return "win"
    return "lose"


def _get_auth(plugin: GamesPlugin):
    """Return the DiscordAuth instance or None."""
    web_app = getattr(getattr(plugin, "web_panel", None), "web_app", None)
    return getattr(web_app, "auth", None)


def _check_auth_and_guild(request: Request, plugin: GamesPlugin, guild_id: str) -> tuple[int | None, int | None, HTMLResponse | None]:
    """Check auth and guild context. Returns (uid, gid, error_response).

    If auth or guild is missing, returns an error HTMLResponse and uid/gid are None.
    If both are present, returns (uid, gid, None).
    """
    auth = _get_auth(plugin)
    if not auth or not auth.is_authenticated(request):
        return (
            None,
            None,
            HTMLResponse('<p class="games-msg games-error">Please <a href="/auth/login">log in</a> to use this feature.</p>'),
        )

    current_user = auth.get_current_user(request)
    try:
        uid = int(current_user["user"]["id"])
    except (KeyError, ValueError, TypeError):
        return None, None, HTMLResponse('<p class="games-msg games-error">Could not determine your user ID.</p>')

    if not guild_id:
        return None, None, HTMLResponse('<p class="games-msg">Select a server from the sidebar to get started.</p>')

    try:
        gid = int(guild_id)
    except ValueError:
        return None, None, HTMLResponse('<p class="games-msg games-error">Invalid Guild ID.</p>')

    return uid, gid, None


def register_games_routes(app: FastAPI, plugin: GamesPlugin) -> None:
    """Register FastAPI routes for the games plugin web panel."""

    @app.get("/plugin/games", response_class=HTMLResponse)
    async def games_panel(request: Request) -> HTMLResponse:
        return plugin.render_plugin_template(request, "panel.html")

    # ------------------------------------------------------------------
    # Section navigation
    # ------------------------------------------------------------------

    @app.get("/plugin/games/api/section/play", response_class=HTMLResponse)
    async def api_section_play(request: Request, guild_id: str = "") -> HTMLResponse:
        """Return the Play section fragment."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err
        return HTMLResponse(_render_play_section())

    @app.get("/plugin/games/api/section/leaderboards", response_class=HTMLResponse)
    async def api_section_leaderboards(request: Request, guild_id: str = "") -> HTMLResponse:
        """Return the Leaderboards section fragment."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err
        return HTMLResponse(_render_leaderboards_section())

    @app.get("/plugin/games/api/section/stats", response_class=HTMLResponse)
    async def api_section_stats(request: Request, guild_id: str = "") -> HTMLResponse:
        """Return the Stats section fragment."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err
        return HTMLResponse(_render_stats_section())

    @app.get("/plugin/games/api/section/achievements", response_class=HTMLResponse)
    async def api_section_achievements(
        request: Request,
        guild_id: str = "",
        game_filter: str = "all",
    ) -> HTMLResponse:
        """Return the Achievements section fragment with the game filter toolbar."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err
        return HTMLResponse(_render_achievements_section(game_filter))

    # ------------------------------------------------------------------
    # Trivia play
    # ------------------------------------------------------------------

    @app.get("/plugin/games/api/trivia/question", response_class=HTMLResponse)
    async def api_trivia_question(
        request: Request,
        guild_id: str = "",
        difficulty: str = "",
        category: str = "",
    ) -> HTMLResponse:
        """Fetch a trivia question and return an HTMX fragment with answer buttons."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err

        diff = difficulty if difficulty in TRIVIA_DIFFICULTIES else None
        cat = category if category in TRIVIA_CATEGORIES else None

        question = await plugin.fetch_trivia_question(gid, diff, cat)
        if not question:
            return HTMLResponse('<p class="games-msg games-error">Failed to get a trivia question. Please try again!</p>')

        # Record server-side start time for time-attack bonus
        _trivia_sessions[(uid, gid)] = time.time()

        return HTMLResponse(_render_trivia_question(question))

    @app.post("/plugin/games/api/trivia/answer", response_class=HTMLResponse)
    async def api_trivia_answer(request: Request) -> HTMLResponse:
        """Process a trivia answer and return the result plus next-question button."""
        form = await request.form()
        guild_id = form.get("guild_id", "")
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err

        selected_answer = form.get("answer", "")
        correct_answer = form.get("correct_answer", "")
        difficulty = form.get("difficulty", "medium")
        used_hint = form.get("used_hint", "false") == "true"
        is_time_attack = form.get("is_time_attack", "false") == "true"

        is_correct = selected_answer == correct_answer

        # Calculate points using the same scoring rules as Discord
        base_points = games_settings.trivia_base_points.get(difficulty, 20)
        if used_hint:
            base_points = int(base_points * games_settings.trivia_hint_penalty)

        # Time-attack bonus using server-side elapsed time
        start_time = _trivia_sessions.pop((uid, gid), None)
        response_time = 0.0
        if start_time:
            response_time = time.time() - start_time
            if is_time_attack and is_correct and response_time <= games_settings.trivia_time_bonus_threshold:
                base_points = int(base_points * games_settings.trivia_time_bonus_multiplier)

        # Award points (records stats + checks achievements)
        await plugin.award_points(
            uid,
            gid,
            base_points if is_correct else 0,
            difficulty,
            used_hint,
            response_time,
            is_correct=is_correct,
        )

        return HTMLResponse(
            _render_trivia_result(
                is_correct,
                correct_answer,
                base_points,
                difficulty,
                used_hint,
                is_time_attack,
                response_time,
                guild_id,
            )
        )

    # ------------------------------------------------------------------
    # Angle game play
    # ------------------------------------------------------------------

    @app.get("/plugin/games/api/angle/image", response_class=Response)
    async def api_angle_image(target: int = 90) -> Response:
        """Generate and return the angle protractor PNG."""
        try:
            target_clamped = max(0, min(360, int(target)))
        except (ValueError, TypeError):
            target_clamped = 90
        png_bytes = generate_angle_image(target_clamped)
        return Response(content=png_bytes, media_type="image/png")

    @app.get("/plugin/games/api/angle/start", response_class=HTMLResponse)
    async def api_angle_start(request: Request, guild_id: str = "") -> HTMLResponse:
        """Start or load the daily angle game and return the game fragment."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err

        state = await plugin.get_or_create_angle_game(uid, gid)
        if not state:
            return HTMLResponse('<p class="games-msg games-error">Failed to start the angle game.</p>')

        return HTMLResponse(_render_angle_game(state, guild_id))

    @app.post("/plugin/games/api/angle/guess", response_class=HTMLResponse)
    async def api_angle_guess(request: Request) -> HTMLResponse:
        """Process an angle guess and return the updated game fragment."""
        form = await request.form()
        guild_id = form.get("guild_id", "")
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err

        raw_guess = form.get("guess", "")
        try:
            guess = int(raw_guess)
            if not 0 <= guess <= 360:
                raise ValueError
        except (ValueError, TypeError):
            return HTMLResponse('<p class="games-msg games-error">Please enter a whole number between 0 and 360.</p>')

        state = await plugin.process_angle_guess(uid, gid, guess)
        if not state:
            return HTMLResponse('<p class="games-msg games-error">Failed to process your guess.</p>')

        return HTMLResponse(_render_angle_game(state, guild_id))

    # ------------------------------------------------------------------
    # RPS play
    # ------------------------------------------------------------------

    @app.post("/plugin/games/api/rps/play", response_class=HTMLResponse)
    async def api_rps_play(request: Request) -> HTMLResponse:
        """Process an RPS move and return the outcome fragment."""
        form = await request.form()
        guild_id = form.get("guild_id", "")
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err

        player_choice = form.get("choice", "")
        if player_choice not in _RPS_CHOICES:
            return HTMLResponse('<p class="games-msg games-error">Invalid choice.</p>')

        bot_choice = random.choice(list(_RPS_CHOICES.keys()))
        result = _rps_determine_result(player_choice, bot_choice)

        await plugin.record_rps_result(uid, gid, player_choice, result)

        return HTMLResponse(_render_rps_result(player_choice, bot_choice, result, guild_id))

    # ------------------------------------------------------------------
    # Leaderboards
    # ------------------------------------------------------------------

    @app.get("/plugin/games/api/leaderboards", response_class=HTMLResponse)
    async def api_leaderboards(
        request: Request,
        guild_id: str = "",
        sort: str = "points",
    ) -> HTMLResponse:
        """Return a leaderboard fragment for the selected guild."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err

        if sort not in ("points", "accuracy", "streak"):
            sort = "points"

        leaderboard_data = await plugin.get_leaderboard(gid, sort)

        return HTMLResponse(_render_leaderboards(leaderboard_data, sort))

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @app.get("/plugin/games/api/stats", response_class=HTMLResponse)
    async def api_stats(request: Request, guild_id: str = "") -> HTMLResponse:
        """Return a stats fragment with trivia and angle stats for the current user."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err

        trivia_stats = await plugin.get_trivia_stats(uid, gid)
        angle_stats = await plugin.get_angle_stats(uid, gid)

        return HTMLResponse(_render_stats(trivia_stats, angle_stats))

    # ------------------------------------------------------------------
    # Achievements (existing, preserved)
    # ------------------------------------------------------------------

    @app.get("/plugin/games/api/achievements", response_class=HTMLResponse)
    async def api_achievements(
        request: Request,
        guild_id: str = "",
        game_filter: str = "all",
    ) -> HTMLResponse:
        """Return an HTMX fragment with achievements for the current user in the selected guild."""
        uid, gid, err = _check_auth_and_guild(request, plugin, guild_id)
        if err:
            return err

        # --- Fetch stats + unlocked achievement IDs ---
        trivia_stats = await plugin.get_trivia_stats(uid, gid)
        angle_stats = await plugin.get_angle_stats(uid, gid)
        rps_stats = await plugin.get_rps_stats(uid, gid)

        trivia_unlocked = {a.achievement_id for a in await plugin.get_trivia_achievements(uid, gid)}
        angle_unlocked = {a.achievement_id for a in await plugin.get_angle_achievements(uid, gid)}
        rps_unlocked = {a.achievement_id for a in await plugin.get_rps_achievements(uid, gid)}

        # --- Build sections ---
        sections: list[dict] = []

        if game_filter in ("all", "trivia"):
            sections.append(
                {
                    "title": "Trivia",
                    "icon": "fa-solid fa-brain",
                    "color": "#9932CC",
                    "achievements": _build_trivia_items(TRIVIA_ACHIEVEMENTS, trivia_unlocked, trivia_stats),
                }
            )

        if game_filter in ("all", "angle"):
            sections.append(
                {
                    "title": "Angle",
                    "icon": "fa-solid fa-drafting-compass",
                    "color": "#E67E22",
                    "achievements": _build_angle_items(ANGLE_ACHIEVEMENTS, angle_unlocked, angle_stats),
                }
            )

        if game_filter in ("all", "rps"):
            sections.append(
                {
                    "title": "Rock Paper Scissors",
                    "icon": "fa-solid fa-hand-back-fist",
                    "color": "#1ABC9C",
                    "achievements": _build_rps_items(RPS_ACHIEVEMENTS, rps_unlocked, rps_stats),
                }
            )

        total_unlocked = len(trivia_unlocked) + len(angle_unlocked) + len(rps_unlocked)
        total_all = len(TRIVIA_ACHIEVEMENTS) + len(ANGLE_ACHIEVEMENTS) + len(RPS_ACHIEVEMENTS)

        return HTMLResponse(_render_achievements(sections, total_unlocked, total_all))


# ---------------------------------------------------------------------------
# Auth/guild helper (re-exported for tests)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Progress helpers
# ---------------------------------------------------------------------------


def _pct(current: int, goal: int) -> int:
    return min(100, int(current / max(goal, 1) * 100))


def _build_trivia_items(definitions: dict, unlocked: set, stats: Any) -> list[dict]:
    items = []
    for ach_id, data in definitions.items():
        req = data["requirement"]
        req_type, req_value = req["type"], req["value"]
        current = 0
        if stats:
            if req_type == "correct_answers":
                current = stats.correct_answers
            elif req_type == "streak":
                current = stats.best_streak
            elif req_type == "fast_answers":
                current = stats.fast_answers
            elif req_type == "hard_correct":
                current = stats.hard_correct
            elif req_type == "total_points":
                current = stats.total_points
            elif req_type == "perfect_accuracy":
                current = 20 if stats.recent_perfect else 0
        label = req_type.replace("_", " ").title()
        items.append(
            {
                "id": ach_id,
                "name": data["name"],
                "description": data["description"],
                "emoji": data["emoji"],
                "unlocked": ach_id in unlocked,
                "current": current,
                "goal": req_value,
                "pct": _pct(current, req_value),
                "progress_label": f"{label}: {current:,} / {req_value:,}",
            }
        )
    return items


def _build_angle_items(definitions: dict, unlocked: set, stats: Any) -> list[dict]:
    items = []
    for ach_id, data in definitions.items():
        req = data["requirement"]
        req_type, req_value = req["type"], req["value"]
        current = 0
        if stats:
            if req_type == "wins":
                current = stats.wins
            elif req_type == "exact_wins":
                current = stats.exact_wins
            elif req_type == "close_wins":
                current = stats.close_wins
            elif req_type == "total_games":
                current = stats.total_games
            elif req_type == "win_streak":
                current = stats.best_win_streak
            elif req_type == "total_points":
                current = stats.total_points
        label = req_type.replace("_", " ").title()
        items.append(
            {
                "id": ach_id,
                "name": data["name"],
                "description": data["description"],
                "emoji": data["emoji"],
                "unlocked": ach_id in unlocked,
                "current": current,
                "goal": req_value,
                "pct": _pct(current, req_value),
                "progress_label": f"{label}: {current:,} / {req_value:,}",
            }
        )
    return items


def _build_rps_items(definitions: dict, unlocked: set, stats: Any) -> list[dict]:
    items = []
    for ach_id, data in definitions.items():
        req = data["requirement"]
        req_type, req_value = req["type"], req["value"]
        current = 0
        if stats:
            if req_type == "wins":
                current = stats.wins
            elif req_type == "total_games":
                current = stats.total_games
            elif req_type == "win_streak":
                current = stats.best_win_streak
            elif req_type == "rock_wins":
                current = stats.rock_wins
            elif req_type == "paper_wins":
                current = stats.paper_wins
            elif req_type == "scissors_wins":
                current = stats.scissors_wins
            elif req_type == "draws":
                current = stats.draws
        label = req_type.replace("_", " ").title()
        items.append(
            {
                "id": ach_id,
                "name": data["name"],
                "description": data["description"],
                "emoji": data["emoji"],
                "unlocked": ach_id in unlocked,
                "current": current,
                "goal": req_value,
                "pct": _pct(current, req_value),
                "progress_label": f"{label}: {current:,} / {req_value:,}",
            }
        )
    return items


# ---------------------------------------------------------------------------
# HTML rendering — section fragments
# ---------------------------------------------------------------------------


def _render_play_section() -> str:
    """Render the Play section with trivia, angle, and RPS game cards."""
    # Build trivia hx-vals as a separate string to avoid line-length issues
    trivia_vals = (
        "js:{guild_id: localStorage.getItem('selectedGuildId') || '', "
        "difficulty: document.getElementById('trivia-difficulty')?.value || '', "
        "category: document.getElementById('trivia-category')?.value || ''}"
    )
    return f"""
<div class="games-play-grid">
  <!-- Trivia -->
  <div class="games-card">
    <div class="games-card-title">
      <i class="fa-solid fa-brain" style="color:#9932CC"></i>
      <span>Trivia</span>
    </div>
    <p class="games-card-desc">Test your knowledge! Pick a difficulty and category, then answer the question.</p>
    <div class="games-card-filters">
      <select id="trivia-difficulty" name="difficulty">
        <option value="">Any difficulty</option>
        <option value="easy">🟢 Easy</option>
        <option value="medium">🟡 Medium</option>
        <option value="hard">🔴 Hard</option>
      </select>
      <select id="trivia-category" name="category">
        <option value="">Any category</option>
        <option value="general">General</option>
        <option value="science">Science</option>
        <option value="history">History</option>
        <option value="geography">Geography</option>
        <option value="sports">Sports</option>
        <option value="music">Music</option>
        <option value="film">Film</option>
        <option value="games">Games</option>
        <option value="computers">Computers</option>
        <option value="animals">Animals</option>
      </select>
    </div>
    <div class="games-card-actions">
      <button class="btn" hx-get="/plugin/games/api/trivia/question"
        hx-vals="{trivia_vals}"
        hx-target="#trivia-result" hx-indicator="#trivia-loading">
        <i class="fa-solid fa-play icon icon-sm"></i> Start Trivia
      </button>
      <span id="trivia-loading" class="htmx-indicator">Loading question…</span>
    </div>
    <div id="trivia-result" class="games-result"></div>
  </div>

  <!-- Angle Game -->
  <div class="games-card">
    <div class="games-card-title">
      <i class="fa-solid fa-drafting-compass" style="color:#E67E22"></i>
      <span>Angle Game</span>
    </div>
    <p class="games-card-desc">Guess the mystery angle! You get 4 attempts with direction hints.</p>
    <div class="games-card-actions">
      <button class="btn" hx-get="/plugin/games/api/angle/start"
        hx-vals="js:{{guild_id: localStorage.getItem('selectedGuildId') || ''}}"
        hx-target="#angle-result" hx-indicator="#angle-loading">
        <i class="fa-solid fa-play icon icon-sm"></i> Start Angle Game
      </button>
      <span id="angle-loading" class="htmx-indicator">Loading…</span>
    </div>
    <div id="angle-result" class="games-result"></div>
  </div>

  <!-- RPS -->
  <div class="games-card">
    <div class="games-card-title">
      <i class="fa-solid fa-hand-back-fist" style="color:#1ABC9C"></i>
      <span>Rock Paper Scissors</span>
    </div>
    <p class="games-card-desc">Pick your move and see if you can beat the bot!</p>
    <div class="games-card-actions games-rps-buttons">
      <button class="btn" hx-post="/plugin/games/api/rps/play"
        hx-vals="js:{{guild_id: localStorage.getItem('selectedGuildId') || '', choice: 'rock'}}"
        hx-target="#rps-result" hx-indicator="#rps-loading">
        🪨 Rock
      </button>
      <button class="btn" hx-post="/plugin/games/api/rps/play"
        hx-vals="js:{{guild_id: localStorage.getItem('selectedGuildId') || '', choice: 'paper'}}"
        hx-target="#rps-result" hx-indicator="#rps-loading">
        📄 Paper
      </button>
      <button class="btn" hx-post="/plugin/games/api/rps/play"
        hx-vals="js:{{guild_id: localStorage.getItem('selectedGuildId') || '', choice: 'scissors'}}"
        hx-target="#rps-result" hx-indicator="#rps-loading">
        ✂️ Scissors
      </button>
      <span id="rps-loading" class="htmx-indicator">Playing…</span>
    </div>
    <div id="rps-result" class="games-result"></div>
  </div>
</div>
"""


def _render_leaderboards_section() -> str:
    """Render the Leaderboards section with a sort selector and results area."""
    return """
<div class="games-toolbar">
  <i class="fa-solid fa-trophy" style="color:var(--accent-color)"></i>
  <label for="lb-sort">Sort by:</label>
  <select id="lb-sort" name="sort"
    hx-get="/plugin/games/api/leaderboards"
    hx-trigger="change, guild-changed from:body"
    hx-target="#lb-results"
    hx-swap="innerHTML"
    hx-vals="js:{guild_id: localStorage.getItem('selectedGuildId') || ''}"
  >
    <option value="points">💎 Points</option>
    <option value="accuracy">🎯 Accuracy</option>
    <option value="streak">🔥 Best Streak</option>
  </select>
  <span class="htmx-indicator">Loading…</span>
</div>
<div id="lb-results"
  hx-get="/plugin/games/api/leaderboards"
  hx-trigger="load"
  hx-vals="js:{guild_id: localStorage.getItem('selectedGuildId') || '', sort: document.getElementById('lb-sort')?.value || 'points'}"
  hx-swap="innerHTML"
>
  <p class="games-msg">Loading…</p>
</div>
"""


def _render_stats_section() -> str:
    """Render the Stats section that auto-loads trivia and angle stats."""
    return """
<div id="stats-results"
  hx-get="/plugin/games/api/stats"
  hx-trigger="load, guild-changed from:body"
  hx-vals="js:{guild_id: localStorage.getItem('selectedGuildId') || ''}"
  hx-swap="innerHTML"
>
  <p class="games-msg">Loading…</p>
</div>
"""


def _render_achievements_section(game_filter: str = "all") -> str:
    """Render the Achievements section with the game filter toolbar and results area."""
    ach_vals = (
        "js:{{guild_id: localStorage.getItem('selectedGuildId') || '', "
        "game_filter: document.getElementById('ach-filter')?.value || 'all'}}"
    )
    sel_all = "selected" if game_filter == "all" else ""
    sel_trivia = "selected" if game_filter == "trivia" else ""
    sel_angle = "selected" if game_filter == "angle" else ""
    sel_rps = "selected" if game_filter == "rps" else ""
    return f"""
<div class="games-toolbar">
  <i class="fa-solid fa-trophy" style="color:var(--accent-color)"></i>
  <label for="ach-filter">Show:</label>
  <select id="ach-filter" name="game_filter"
    hx-get="/plugin/games/api/achievements"
    hx-trigger="change, guild-changed from:body"
    hx-target="#ach-results"
    hx-swap="innerHTML"
    hx-vals="js:{{guild_id: localStorage.getItem('selectedGuildId') || ''}}"
  >
    <option value="all" {sel_all}>All games</option>
    <option value="trivia" {sel_trivia}>Trivia</option>
    <option value="angle" {sel_angle}>Angle</option>
    <option value="rps" {sel_rps}>Rock Paper Scissors</option>
  </select>
  <span class="htmx-indicator">Loading…</span>
</div>
<div id="ach-results"
  hx-get="/plugin/games/api/achievements"
  hx-trigger="load"
  hx-vals="{ach_vals}"
  hx-swap="innerHTML"
>
  <p class="games-msg">Loading…</p>
</div>
"""


# ---------------------------------------------------------------------------
# HTML rendering — trivia
# ---------------------------------------------------------------------------


def _render_trivia_question(question: dict[str, Any]) -> str:
    """Render a trivia question fragment with answer buttons and a countdown timer."""
    question_text = html.escape(question["question"])
    category = html.escape(str(question.get("category", "General")))
    difficulty = question.get("difficulty", "medium")
    diff_emoji = DIFFICULTY_EMOJIS.get(difficulty, "⚪")
    correct_answer = question["correct_answer"]
    all_answers = question["all_answers"]

    # 10% chance of time attack
    is_time_attack = random.random() < 0.1
    timeout = games_settings.trivia_timeout_seconds

    buttons_html = ""
    for answer in all_answers:
        escaped = html.escape(answer)
        buttons_html += (
            f'<button class="btn games-answer-btn" '
            f'hx-post="/plugin/games/api/trivia/answer" '
            f'hx-vals=\'js:{{answer: "{escaped}", correct_answer: "{html.escape(correct_answer)}", '
            f'difficulty: "{difficulty}", guild_id: localStorage.getItem("selectedGuildId") || "", '
            f'is_time_attack: "{"true" if is_time_attack else "false"}"}}\' '
            f'hx-target="#trivia-result" hx-indicator="#trivia-loading">'
            f"{escaped}</button>\n"
        )

    time_attack_badge = ""
    if is_time_attack:
        time_attack_badge = '<span class="games-badge games-badge-time">⚡ Time Attack</span>'

    return f"""
<div class="games-trivia-question">
  <div class="games-question-meta">
    <span class="games-badge">{diff_emoji} {difficulty.title()}</span>
    <span class="games-badge">📂 {category}</span>
    {time_attack_badge}
    <span class="games-timer" id="trivia-timer" data-timeout="{timeout}">⏱️ {timeout}s</span>
  </div>
  <div class="games-question-text">{question_text}</div>
  <div class="games-answer-buttons">
    {buttons_html}
  </div>
  <script>
  (function() {{
    var el = document.getElementById('trivia-timer');
    if (!el) return;
    var remaining = {timeout};
    var interval = setInterval(function() {{
      remaining--;
      if (remaining <= 0) {{
        clearInterval(interval);
        el.textContent = '⏱️ Time up!';
        el.classList.add('games-timer-expired');
      }} else {{
        el.textContent = '⏱️ ' + remaining + 's';
      }}
    }}, 1000);
    el._timerInterval = interval;
  }})();
  </script>
</div>
"""


def _render_trivia_result(
    is_correct: bool,
    correct_answer: str,
    points: int,
    difficulty: str,
    used_hint: bool,
    is_time_attack: bool,
    response_time: float,
    guild_id: str,
) -> str:
    """Render the trivia answer result with a next-question button."""
    escaped_correct = html.escape(correct_answer)
    if is_correct:
        result_class = "games-correct"
        icon = "✅"
        title = "Correct!"
        details = f"+{points} points"
        if is_time_attack and response_time <= games_settings.trivia_time_bonus_threshold:
            details += " ⚡ (time attack bonus!)"
        if used_hint:
            details += " 💡 (hint penalty applied)"
    else:
        result_class = "games-incorrect"
        icon = "❌"
        title = "Incorrect!"
        details = f"The correct answer was: <strong>{escaped_correct}</strong>"

    # Build vals for next question — read current filter values from DOM
    next_vals = (
        f"js:{{guild_id: '{guild_id}', "
        "difficulty: document.getElementById('trivia-difficulty')?.value || '', "
        "category: document.getElementById('trivia-category')?.value || ''}}"
    )
    return f"""
<div class="games-trivia-result {result_class}">
  <div class="games-result-icon">{icon}</div>
  <div class="games-result-title">{title}</div>
  <div class="games-result-details">{details}</div>
  <div class="games-result-actions">
    <button class="btn" hx-get="/plugin/games/api/trivia/question"
      hx-vals="{next_vals}"
      hx-target="#trivia-result" hx-indicator="#trivia-loading">
      <i class="fa-solid fa-forward icon icon-sm"></i> Next Question
    </button>
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# HTML rendering — angle game
# ---------------------------------------------------------------------------


def _render_angle_game(state: dict[str, Any], guild_id: str) -> str:
    """Render the angle game fragment with image, guess history, and input form."""
    target = state.get("target", 90)
    guesses = state.get("guesses", [])
    is_complete = state.get("is_complete", False)
    won = state.get("won", False)
    attempts_remaining = state.get("attempts_remaining", ANGLE_MAX_ATTEMPTS)
    points_eligible = state.get("points_eligible", True)
    points_awarded = state.get("points_awarded", 0)

    # Build guess history
    from ..plugin import GamesPlugin  # noqa: PLC0415

    history_html = ""
    attempt_colors = ["🟡", "🟣", "🔴", "🟢"]
    for i, guess in enumerate(guesses):
        dist = GamesPlugin.angle_distance(guess, target)
        direction = GamesPlugin.angle_direction(guess, target)
        color_dot = attempt_colors[i % len(attempt_colors)]
        if dist == 0:
            feedback = "✅ **Exact!**"
        else:
            arrow = "⬆️" if direction == "higher" else "⬇️"
            feedback = f"{arrow} Go {direction} ({dist}° off)"
        history_html += f"<div class='games-angle-guess'>{color_dot} #{i + 1}: <strong>{guess}°</strong> — {feedback}</div>\n"

    # Build image URL
    img_url = f"/plugin/games/api/angle/image?target={target}"

    # Status / result
    if is_complete and won:
        status_html = f"<div class='games-angle-result games-correct'>🎉 You got it! The angle was <strong>{target}°</strong>"
        if points_eligible and points_awarded > 0:
            status_html += f" — +{points_awarded} points"
        elif not points_eligible:
            status_html += " (no points — replay)"
        status_html += "</div>"
    elif is_complete and not won:
        status_html = (
            "<div class='games-angle-result games-incorrect'>" f"💀 Out of attempts! The angle was <strong>{target}°</strong></div>"
        )
    else:
        remaining_text = f"{attempts_remaining} attempt(s) remaining"
        if not points_eligible:
            remaining_text += " *(replay — no points)*"
        status_html = f"<div class='games-angle-status'>{remaining_text}</div>"

    # Guess form (only if game is still in progress)
    form_html = ""
    if not is_complete:
        form_html = f"""
<form class="games-angle-form" hx-post="/plugin/games/api/angle/guess"
  hx-vals="js:{{guild_id: '{guild_id}'}}"
  hx-target="#angle-result" hx-indicator="#angle-loading">
  <input type="number" name="guess" min="0" max="360" placeholder="0–360" required>
  <button type="submit" class="btn"><i class="fa-solid fa-crosshairs icon icon-sm"></i> Guess</button>
</form>
"""
    else:
        form_html = f"""
<div class="games-angle-replay">
  <button class="btn" hx-get="/plugin/games/api/angle/start"
    hx-vals="js:{{guild_id: '{guild_id}'}}"
    hx-target="#angle-result" hx-indicator="#angle-loading">
    <i class="fa-solid fa-rotate-right icon icon-sm"></i> Play Again
  </button>
</div>
"""

    return f"""
<div class="games-angle-game">
  <div class="games-angle-image">
    <img src="{img_url}" alt="Mystery angle" width="300" height="300">
  </div>
  <div class="games-angle-history">
    {history_html}
  </div>
  {status_html}
  {form_html}
</div>
"""


# ---------------------------------------------------------------------------
# HTML rendering — RPS
# ---------------------------------------------------------------------------


def _render_rps_result(player_choice: str, bot_choice: str, result: str, guild_id: str) -> str:
    """Render the RPS outcome fragment with play-again buttons."""
    player_info = _RPS_CHOICES[player_choice]
    bot_info = _RPS_CHOICES[bot_choice]

    if result == "win":
        result_class = "games-correct"
        icon = "🎉"
        title = "You win!"
    elif result == "lose":
        result_class = "games-incorrect"
        icon = "💀"
        title = "You lose!"
    else:
        result_class = "games-draw"
        icon = "🤝"
        title = "It's a draw!"

    return f"""
<div class="games-rps-result {result_class}">
  <div class="games-result-icon">{icon}</div>
  <div class="games-result-title">{title}</div>
  <div class="games-result-details">
    You: {player_info['emoji']} <strong>{player_info['label']}</strong> |
    Bot: {bot_info['emoji']} <strong>{bot_info['label']}</strong>
  </div>
  <div class="games-rps-play-again">
    <button class="btn" hx-post="/plugin/games/api/rps/play"
      hx-vals="js:{{guild_id: '{guild_id}', choice: 'rock'}}"
      hx-target="#rps-result" hx-indicator="#rps-loading">🪨 Rock</button>
    <button class="btn" hx-post="/plugin/games/api/rps/play"
      hx-vals="js:{{guild_id: '{guild_id}', choice: 'paper'}}"
      hx-target="#rps-result" hx-indicator="#rps-loading">📄 Paper</button>
    <button class="btn" hx-post="/plugin/games/api/rps/play"
      hx-vals="js:{{guild_id: '{guild_id}', choice: 'scissors'}}"
      hx-target="#rps-result" hx-indicator="#rps-loading">✂️ Scissors</button>
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# HTML rendering — leaderboards
# ---------------------------------------------------------------------------


def _render_leaderboards(data: list[dict], sort: str) -> str:
    """Render a leaderboard table or empty state."""
    if not data:
        return '<p class="games-msg">No trivia data available yet! Start playing to see rankings.</p>'

    sort_labels = {"points": "Points", "accuracy": "Accuracy", "streak": "Best Streak"}
    label = sort_labels.get(sort, sort.title())

    rows = ""
    for i, entry in enumerate(data[:10], 1):
        medal = ""
        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"

        value = entry.get(sort, 0)
        if sort == "accuracy":
            value_str = f"{value:.1f}%"
        else:
            value_str = f"{value:,}"

        rows += (
            f"<tr><td class='games-lb-rank'>{medal} #{i}</td>"
            f"<td class='games-lb-user'><@{entry['user_id']}></td>"
            f"<td class='games-lb-value'>{value_str}</td></tr>\n"
        )

    return f"""
<div class="games-leaderboard">
  <h3 class="games-section-title">🏆 Trivia Leaderboard — {label}</h3>
  <table class="games-lb-table">
    <thead><tr><th>Rank</th><th>Player</th><th>{label}</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""


# ---------------------------------------------------------------------------
# HTML rendering — stats
# ---------------------------------------------------------------------------


def _stat_item(label: str, value: Any) -> str:
    """Render a single stat item div."""
    return (
        f'<div class="games-stat-item">'
        f'<span class="games-stat-label">{label}</span>'
        f'<span class="games-stat-value">{value}</span></div>'
    )


def _render_stats(trivia_stats: Any, angle_stats: Any) -> str:
    """Render the stats fragment with trivia and angle stats cards."""
    has_data = False

    # Trivia stats card
    if trivia_stats and trivia_stats.total_questions > 0:
        has_data = True
        items = [
            _stat_item("Questions", f"{trivia_stats.total_questions:,}"),
            _stat_item("Correct", f"{trivia_stats.correct_answers:,}"),
            _stat_item("Accuracy", f"{trivia_stats.accuracy:.1f}%"),
            _stat_item("Total Points", f"{trivia_stats.total_points:,}"),
            _stat_item("🟢 Easy", f"{trivia_stats.easy_correct:,}"),
            _stat_item("🟡 Medium", f"{trivia_stats.medium_correct:,}"),
            _stat_item("🔴 Hard", f"{trivia_stats.hard_correct:,}"),
            _stat_item("Current Streak", trivia_stats.current_streak),
            _stat_item("Best Streak", trivia_stats.best_streak),
            _stat_item("Fast Answers", trivia_stats.fast_answers),
            _stat_item("Hints Used", trivia_stats.hints_used),
        ]
        trivia_html = (
            '<div class="games-stats-card">'
            '<h3 class="games-section-title">'
            '<i class="fa-solid fa-brain" style="color:#9932CC"></i> Trivia Stats</h3>'
            f'<div class="games-stats-grid">{"".join(items)}</div>'
            "</div>"
        )
    else:
        trivia_html = (
            '<div class="games-stats-card">'
            '<h3 class="games-section-title">'
            '<i class="fa-solid fa-brain" style="color:#9932CC"></i> Trivia Stats</h3>'
            '<p class="games-msg">You haven\'t played trivia yet! '
            "Visit the Play section to start.</p>"
            "</div>"
        )

    # Angle stats card
    if angle_stats and angle_stats.total_games > 0:
        has_data = True
        items = [
            _stat_item("Games Played", f"{angle_stats.total_games:,}"),
            _stat_item("Wins", f"{angle_stats.wins:,}"),
            _stat_item("Win Rate", f"{angle_stats.win_rate:.1f}%"),
            _stat_item("Total Points", f"{angle_stats.total_points:,}"),
            _stat_item("Perfect Guesses", f"{angle_stats.exact_wins:,}"),
            _stat_item("Close Wins (≤2°)", f"{angle_stats.close_wins:,}"),
            _stat_item("Current Streak", angle_stats.current_win_streak),
            _stat_item("Best Streak", angle_stats.best_win_streak),
        ]
        angle_html = (
            '<div class="games-stats-card">'
            '<h3 class="games-section-title">'
            '<i class="fa-solid fa-drafting-compass" style="color:#E67E22"></i> '
            "Angle Stats</h3>"
            f'<div class="games-stats-grid">{"".join(items)}</div>'
            "</div>"
        )
    else:
        angle_html = (
            '<div class="games-stats-card">'
            '<h3 class="games-section-title">'
            '<i class="fa-solid fa-drafting-compass" style="color:#E67E22"></i> '
            "Angle Stats</h3>"
            '<p class="games-msg">You haven\'t played the angle game yet! '
            "Visit the Play section to start.</p>"
            "</div>"
        )

    if not has_data:
        return '<p class="games-msg">You haven\'t played any games yet. ' "Visit the Play section to get started!</p>"

    return f'<div class="games-stats-container">{trivia_html}{angle_html}</div>'


# ---------------------------------------------------------------------------
# HTML rendering — achievements (existing, preserved)
# ---------------------------------------------------------------------------


def _render_achievements(sections: list[dict], total_unlocked: int, total_all: int) -> str:
    overall_pct = _pct(total_unlocked, total_all)
    html_str = f"""
<div class="ach-summary">
  <div class="ach-summary-bar-wrap">
    <span class="ach-summary-label">Overall progress</span>
    <span class="ach-summary-count">{total_unlocked} / {total_all}</span>
  </div>
  <div class="ach-progress-bar-bg">
    <div class="ach-progress-bar-fill" style="width:{overall_pct}%"></div>
  </div>
</div>
"""
    for section in sections:
        unlocked_count = sum(1 for a in section["achievements"] if a["unlocked"])
        section_total = len(section["achievements"])
        html_str += f"""
<div class="ach-section">
  <h3 class="ach-section-title">
    <i class="{section['icon']}" style="color:{section['color']}"></i>
    {section['title']}
    <span class="ach-section-count">{unlocked_count}/{section_total}</span>
  </h3>
  <div class="ach-grid">
"""
        for ach in section["achievements"]:
            if ach["unlocked"]:
                html_str += f"""
    <div class="ach-card ach-unlocked">
      <div class="ach-emoji">{ach['emoji']}</div>
      <div class="ach-body">
        <div class="ach-name">{ach['name']}</div>
        <div class="ach-desc">{ach['description']}</div>
        <div class="ach-badge-unlocked">Unlocked</div>
      </div>
    </div>
"""
            else:
                html_str += f"""
    <div class="ach-card ach-locked">
      <div class="ach-emoji ach-emoji-locked">{ach['emoji']}</div>
      <div class="ach-body">
        <div class="ach-name">{ach['name']}</div>
        <div class="ach-desc">{ach['description']}</div>
        <div class="ach-progress-wrap">
          <div class="ach-progress-label">{ach['progress_label']}</div>
          <div class="ach-progress-bar-bg ach-progress-bar-sm">
            <div class="ach-progress-bar-fill ach-progress-bar-locked" style="width:{ach['pct']}%"></div>
          </div>
        </div>
      </div>
    </div>
"""
        html_str += "  </div>\n</div>\n"
    return html_str
