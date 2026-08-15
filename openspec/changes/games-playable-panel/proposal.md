## Why
The games plugin's web panel currently only shows achievements, even though the plugin has rich interactive games (trivia, angle, RPS) and detailed stats/leaderboards already available through Discord commands. Because the framework is the product and this plugin is meant to be the reference implementation for interactive web panels, the panel should let users actually play the games and browse their stats — not just view badges.

## What Changes
- Make trivia playable from the web panel via HTMX: fetch a question, click an answer button, POST the choice, and receive the result plus the next question. Scoring, streaks, and stats recording reuse the same logic and database models as Discord-played trivia (single-player only on web).
- Make the angle game playable from the web panel: render the daily protractor image via a dedicated image-generation route, accept a guess through an HTMX form, and return the updated image plus a direction hint and degree distance. Reuses the daily seeded angle, 4-attempt limit, and points-for-precision rules.
- Make rock-paper-scissors playable from the web panel: click rock/paper/scissors buttons, POST the choice, and receive the bot's move and outcome. Reuses the existing RPS stats recording.
- Add a leaderboards view to the panel that surfaces the trivia leaderboard (points, accuracy, streak) for the selected guild, mirroring `/trivia-leaderboard`.
- Add a detailed stats view to the panel that surfaces trivia stats (`/trivia-stats`) and angle stats (`/angle-stats`) for the current user in the selected guild.
- Add an image-generation route that produces the matplotlib protractor PNG for the angle game, so the web panel can display the same visual feedback as the Discord command.
- Add tests for the games plugin (none currently exist under `tests/unit/plugins/games/`): game logic (scoring, angle distance/direction, daily seeding), web routes (playable trivia/angle/RPS, leaderboards, stats, image generation), and stats recording.

## Capabilities

### New Capabilities
None — this modifies an existing capability.

### Modified Capabilities
- `plugins/games`: Add requirements for playable web trivia, playable web angle game (with image-generation route), playable web RPS, a web leaderboards view, a web stats view, and test coverage for the games plugin's game logic, web routes, and stats recording.

## Impact
- **Affected code:**
  - `plugins/games/web/routes.py` — new HTMX endpoints for trivia play (fetch question, submit answer), angle play (start game, submit guess), RPS play (submit move), leaderboards, stats, and a PNG image-generation route for the angle protractor.
  - `plugins/games/templates/panel.html` — new tabbed/sectioned UI for Play, Leaderboards, Stats, and Achievements; HTMX-driven interactive game fragments.
  - `plugins/games/plugin.py` — may extract shared question-fetch/scoring helpers so the web routes can reuse them without duplicating command logic; the existing `award_points`, `process_angle_guess`, `record_rps_result`, `get_leaderboard`, and stats helpers are already reusable.
  - `plugins/games/utils/angle_image.py` — reused as-is by the new image route (no Discord-specific dependencies).
- **APIs:** New REST endpoints under `/plugin/games/api/...` for trivia question fetch/answer, angle start/guess/image, RPS move, leaderboards, and stats. All require Discord OAuth authentication and a selected guild context. Existing achievement endpoints are unchanged.
- **Dependencies:** No new runtime dependencies; matplotlib is already required for the angle command. HTMX is the established panel interactivity pattern (see fun and music panels).
- **Tests:** New test modules under `tests/unit/plugins/games/` covering game logic, web routes, and stats recording; existing tests for other plugins remain valid.
