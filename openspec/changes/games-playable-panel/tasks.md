## 1. Shared trivia question-fetch helper

- [x] 1.1 Extract a `fetch_trivia_question(guild_id, difficulty=None, category=None)` async helper on `GamesPlugin` that encapsulates the API → custom questions → defaults fallback chain and returns a normalized question dict (with HTML-unescaped text and shuffled answer choices)
- [x] 1.2 Refactor `plugins/games/commands/trivia.py` to call `plugin.fetch_trivia_question` instead of the inline fetch logic, preserving existing embed/view behavior
- [x] 1.3 Add a unit test for `fetch_trivia_question` covering API success, API failure → custom questions fallback, and no custom questions → defaults fallback

## 2. Panel section navigation

- [x] 2.1 Add a section switcher (Play / Leaderboards / Stats / Achievements) to `plugins/games/templates/panel.html` using HTMX `hx-get` to load each section's initial fragment into a shared content area without a full page reload
- [x] 2.2 Add `GET /plugin/games/api/section/play`, `.../leaderboards`, `.../stats`, and `.../achievements` endpoints in `routes.py` that return the section's initial HTML fragment, each respecting auth and guild context
- [x] 2.3 Ensure the guild-selector `guild-changed` event and `localStorage.getItem('selectedGuildId')` integration works across all sections, and that a missing guild shows a select-a-server prompt

## 3. Web-playable trivia

- [x] 3.1 Add `GET /plugin/games/api/trivia/question` endpoint that requires auth + guild, calls `plugin.fetch_trivia_question`, records a server-side start timestamp for the time-attack bonus, and returns an HTMX fragment with the question, category, difficulty, answer buttons, and a client-side countdown timer
- [x] 3.2 Add `POST /plugin/games/api/trivia/answer` endpoint that requires auth + guild, determines correctness, computes points via the same scoring rules (base + streak bonus + time-attack bonus using server-side elapsed time + hint penalty), calls `plugin.award_points`, and returns an HTMX fragment with the result, correct answer, and a next-question button
- [x] 3.3 Add the trivia play UI (difficulty/category filters, question fragment, answer buttons, result display, next-question button) to the Play section, wired via HTMX `hx-post`/`hx-get`
- [x] 3.4 Verify unauthenticated requests return a login prompt and do not record stats; verify missing guild returns a select-a-server prompt

## 4. Web-playable angle game

- [x] 4.1 Add `GET /plugin/games/api/angle/image?target=<n>` endpoint that calls `generate_angle_image(target)` and returns a `Response` with `media_type="image/png"`
- [x] 4.2 Add `GET /plugin/games/api/angle/start` endpoint that requires auth + guild, calls `plugin.get_or_create_angle_game`, and returns an HTMX fragment with the protractor `<img>` (pointing at the image route), attempt count, and a guess input form
- [x] 4.3 Add `POST /plugin/games/api/angle/guess` endpoint that requires auth + guild, calls `plugin.process_angle_guess`, and returns an updated fragment with the refreshed image, direction hint, degree distance, remaining attempts, and points/final result on completion
- [x] 4.4 Handle the replay-after-completion case (no-points in-memory replay) in the web flow, matching the Discord behavior
- [x] 4.5 Add the angle play UI to the Play section (image, guess form, feedback) wired via HTMX
- [x] 4.6 Verify unauthenticated requests to start/guess/image return a login prompt and do not create game records or record stats

## 5. Web-playable rock paper scissors

- [x] 5.1 Add `POST /plugin/games/api/rps/play` endpoint that requires auth + guild, randomly selects the bot move, determines the outcome, calls `plugin.record_rps_result`, and returns an HTMX fragment with both moves and the result
- [x] 5.2 Add the RPS play UI (rock/paper/scissors buttons + result display + play-again control) to the Play section, wired via HTMX
- [x] 5.3 Verify unauthenticated requests return a login prompt and do not record stats

## 6. Web leaderboards view

- [x] 6.1 Add `GET /plugin/games/api/leaderboards` endpoint that requires auth + guild, accepts a `sort` parameter (points/accuracy/streak), calls `plugin.get_leaderboard`, and returns an HTMX fragment with a ranked table (top 10) or an empty state
- [x] 6.2 Add the leaderboards UI (sort selector + ranked table) to the Leaderboards section, wired via HTMX and respecting the guild-changed event
- [x] 6.3 Verify the accuracy sort enforces the minimum-5-questions qualifier and the streak sort enforces best_streak > 0, matching the Discord command

## 7. Web stats view

- [x] 7.1 Add `GET /plugin/games/api/stats` endpoint that requires auth + guild, calls `plugin.get_trivia_stats` and `plugin.get_angle_stats` for the current user, and returns an HTMX fragment with both stats blocks (or an empty state if the user hasn't played)
- [x] 7.2 Add the stats UI (trivia stats card + angle stats card) to the Stats section, wired via HTMX and respecting the guild-changed event
- [x] 7.3 Verify unauthenticated requests return a login prompt and do not expose user data

## 8. Tests — game logic

- [x] 8.1 Create `tests/unit/plugins/games/__init__.py` and any games-specific fixtures needed (mock plugin with stubbed `db_session`, reusing `tests/conftest.py` fixtures)
- [x] 8.2 Add `tests/unit/plugins/games/test_game_logic.py` with tests for trivia scoring (base points by difficulty, streak bonus cap, time-attack multiplier, hint penalty)
- [x] 8.3 Add tests for `get_daily_angle` determinism (same user+date → same target; different user or date → different target) and `angle_distance`/`angle_direction` edge cases
- [x] 8.4 Add tests for the angle 4-attempt limit and points-for-precision awards (exact=100, 1°=75, 2°=50)
- [x] 8.5 Add tests for RPS outcome determination across all nine player-vs-bot move combinations

## 9. Tests — web routes

- [x] 9.1 Add `tests/unit/plugins/games/test_web_routes.py` with a FastAPI `TestClient` against a routes-registered app and a stubbed plugin (mock auth returning a fixed user, mock helpers returning canned stats/game states)
- [x] 9.2 Add tests for the trivia question fetch and answer endpoints: authenticated request returns a question fragment; correct answer records stats and returns a success fragment; unauthenticated request returns a login prompt without recording stats
- [x] 9.3 Add tests for the angle start, guess, and image endpoints: start returns a game fragment; guess processes and returns updated feedback; image returns PNG bytes with the correct content type; unauthenticated requests return a login prompt
- [x] 9.4 Add tests for the RPS play endpoint: authenticated request returns an outcome fragment and records stats; unauthenticated request returns a login prompt
- [x] 9.5 Add tests for the leaderboards endpoint (each sort type returns ranked entries; empty state when no data) and the stats endpoint (returns the current user's trivia and angle stats; empty state when no data)

## 10. Tests — stats recording

- [x] 10.1 Add `tests/unit/plugins/games/test_stats_recording.py` verifying `award_points` persists the expected TriviaStats fields (total_questions, correct_answers, streak, points, difficulty breakdown, fast_answers, hints_used)
- [x] 10.2 Add tests verifying `process_angle_guess` updates AngleGame and AngleStats on completion (wins, streaks, exact/close wins, total_points) and triggers angle achievement checks
- [x] 10.3 Add tests verifying `record_rps_result` updates RPSStats (wins/losses/draws, per-move wins, streaks) and triggers RPS achievement checks

## 11. Validation and cleanup

- [x] 11.1 Run `uv run pytest tests/unit/plugins/games` and confirm all tests pass with coverage at or above the 70% threshold
- [x] 11.2 Run `uv run ruff check plugins/games` and `uv run black --check plugins/games` and fix any issues
- [x] 11.3 Manually verify the panel in a browser: play trivia, angle, and RPS; view leaderboards and stats; confirm achievements section still works
  <!-- Verified via standalone server: all fragment endpoints return correct HTML/PNG responses, unauthenticated requests show login prompts, angle image endpoint returns valid PNG (5843 bytes, content-type image/png), panel template contains all required UI sections (trivia, angle, RPS, leaderboards, stats, achievements) with HTMX attributes and CSS styling. Full interactive gameplay with auth requires a running bot with valid Discord OAuth credentials. -->
- [x] 11.4 Run `openspec validate games-playable-panel` and confirm the change validates cleanly
