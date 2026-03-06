"""FastAPI routes for the games plugin web panel."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from ..config import ANGLE_ACHIEVEMENTS, RPS_ACHIEVEMENTS, TRIVIA_ACHIEVEMENTS

if TYPE_CHECKING:
    from ..plugin import GamesPlugin


def register_games_routes(app: FastAPI, plugin: "GamesPlugin") -> None:
    """Register FastAPI routes for the games plugin web panel."""

    @app.get("/plugin/games", response_class=HTMLResponse)
    async def games_panel(request: Request) -> HTMLResponse:
        return plugin.render_plugin_template(request, "panel.html")

    @app.get("/plugin/games/api/achievements", response_class=HTMLResponse)
    async def api_achievements(
        request: Request,
        user_id: str = "",
        guild_id: str = "",
        game_filter: str = "all",
    ) -> HTMLResponse:
        """Return an HTMX fragment showing all achievements with attained/progress info."""
        if not user_id or not guild_id:
            return HTMLResponse(
                '<p class="ach-placeholder">Enter a User ID and Guild ID above, then click Load.</p>'
            )

        try:
            uid = int(user_id)
            gid = int(guild_id)
        except ValueError:
            return HTMLResponse('<p class="ach-error">Invalid User ID or Guild ID — must be integers.</p>')

        # --- Fetch stats + unlocked achievements ---
        trivia_stats = await plugin.get_trivia_stats(uid, gid)
        angle_stats = await plugin.get_angle_stats(uid, gid)
        rps_stats = await plugin.get_rps_stats(uid, gid)

        trivia_unlocked = {a.achievement_id for a in await plugin.get_trivia_achievements(uid, gid)}
        angle_unlocked = {a.achievement_id for a in await plugin.get_angle_achievements(uid, gid)}
        rps_unlocked = {a.achievement_id for a in await plugin.get_rps_achievements(uid, gid)}

        # --- Build section data ---
        sections: list[dict] = []

        if game_filter in ("all", "trivia"):
            sections.append({
                "title": "Trivia",
                "icon": "fa-solid fa-brain",
                "color": "#9932CC",
                "achievements": _build_trivia_items(TRIVIA_ACHIEVEMENTS, trivia_unlocked, trivia_stats),
            })

        if game_filter in ("all", "angle"):
            sections.append({
                "title": "Angle",
                "icon": "fa-solid fa-drafting-compass",
                "color": "#E67E22",
                "achievements": _build_angle_items(ANGLE_ACHIEVEMENTS, angle_unlocked, angle_stats),
            })

        if game_filter in ("all", "rps"):
            sections.append({
                "title": "Rock Paper Scissors",
                "icon": "fa-solid fa-hand-back-fist",
                "color": "#1ABC9C",
                "achievements": _build_rps_items(RPS_ACHIEVEMENTS, rps_unlocked, rps_stats),
            })

        total_unlocked = len(trivia_unlocked) + len(angle_unlocked) + len(rps_unlocked)
        total_all = len(TRIVIA_ACHIEVEMENTS) + len(ANGLE_ACHIEVEMENTS) + len(RPS_ACHIEVEMENTS)

        return HTMLResponse(_render_achievements(sections, total_unlocked, total_all))


# ---------------------------------------------------------------------------
# Progress helpers
# ---------------------------------------------------------------------------

def _pct(current: int, goal: int) -> int:
    return min(100, int(current / max(goal, 1) * 100))


def _build_trivia_items(definitions: dict, unlocked: set, stats: object | None) -> list[dict]:
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
        items.append({
            "id": ach_id,
            "name": data["name"],
            "description": data["description"],
            "emoji": data["emoji"],
            "unlocked": ach_id in unlocked,
            "current": current,
            "goal": req_value,
            "pct": _pct(current, req_value),
            "progress_label": f"{label}: {current:,} / {req_value:,}",
        })
    return items


def _build_angle_items(definitions: dict, unlocked: set, stats: object | None) -> list[dict]:
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
        items.append({
            "id": ach_id,
            "name": data["name"],
            "description": data["description"],
            "emoji": data["emoji"],
            "unlocked": ach_id in unlocked,
            "current": current,
            "goal": req_value,
            "pct": _pct(current, req_value),
            "progress_label": f"{label}: {current:,} / {req_value:,}",
        })
    return items


def _build_rps_items(definitions: dict, unlocked: set, stats: object | None) -> list[dict]:
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
        items.append({
            "id": ach_id,
            "name": data["name"],
            "description": data["description"],
            "emoji": data["emoji"],
            "unlocked": ach_id in unlocked,
            "current": current,
            "goal": req_value,
            "pct": _pct(current, req_value),
            "progress_label": f"{label}: {current:,} / {req_value:,}",
        })
    return items


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def _render_achievements(sections: list[dict], total_unlocked: int, total_all: int) -> str:
    overall_pct = _pct(total_unlocked, total_all)
    html = f"""
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
        html += f"""
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
                html += f"""
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
                html += f"""
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
        html += "  </div>\n</div>\n"

    return html
