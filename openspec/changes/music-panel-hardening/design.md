## Context

The music plugin ships a 14-route FastAPI web panel plus a WebSocket endpoint (`plugins/music/web/routes.py`) on top of the framework's `WebPanelMixin`. The framework already provides `DiscordAuth` (`bot/web/auth.py`) which stores the authenticated user's Discord guild list in `request.session["guilds"]` after OAuth. Today the music routes read `guild_id` straight from form data / path params with no check, so any logged-in panel user can drive any guild's player. Separately, the web volume control allows 0-150 while the `/volume` Discord command (`plugins/music/commands/voice.py`) and `max_volume` config (default 100) cap at 100; `/seek` and `/position` (`plugins/music/commands/playback.py`) mutate/read player position without broadcasting, so the panel drifts; and the "Previous track" web control is a stub. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- Make every music web route and the WebSocket endpoint refuse to act on a guild the authenticated user does not belong to, using only data already in the session.
- Align web volume bounds with the Discord command (0-100) and the `max_volume` config.
- Make `/seek` and `/position` broadcast WebSocket updates so the panel stays in sync.
- Decide and implement a single, coherent behavior for the previous-track control (implement via history, or remove the button).
- Establish the first unit-test suite for the music plugin covering the above.

**Non-Goals:**
- Per-track or per-command Discord permission-node enforcement inside web routes (web authorization is guild-membership based; Discord permission nodes continue to apply to slash/prefix commands only).
- Rebuilding the panel UI, adding new features, or changing the REST response shapes for successful requests.
- Adding Redis or new external dependencies.
- Changing the `DiscordAuth` OAuth flow itself.

## Decisions

### 1. Authorization source: session guild list, not live API calls
Use `DiscordAuth.get_current_user(request)` and the `guilds` array already cached in the session (`request.session["guilds"]`) to validate that the supplied `guild_id` is one of the user's guilds. Do not make a live Discord API call per request.

**Rationale:** The session already contains the user's guilds from OAuth; a per-request API call would add latency, rate-limit risk, and a failure mode that complicates the 403 path. Guild membership at OAuth time is sufficient for a control panel (this matches how the existing admin panel selects guilds).

**Alternatives considered:**
- Live `/users/@me/guilds` lookup per request: rejected for latency/rate limits and because it introduces an ambiguous error path (API down vs. unauthorized).
- Bot-side cache membership check: rejected because the web process may not share the bot's guild cache and it would couple the web layer to gateway state.

### 2. A single shared authorization helper applied to every route
Introduce one async helper (e.g. `assert_guild_access(request, guild_id) -> user`) that returns the authenticated user or raises an `HTTPException` (401 when unauthenticated, 403 when the guild is not in the user's list). Every REST handler and the WebSocket `accept` path call it before touching the player. WebSocket: perform the check before `websocket.accept()`, and close with policy-violation code 1008 when unauthorized (so no music state is ever sent).

**Rationale:** One helper guarantees the 14 routes stay consistent and makes the test a single assertion per route. Centralizing also makes this the reference pattern for other `WebPanelMixin` plugins.

**Alternatives considered:**
- FastAPI dependency (`Depends`): viable and idiomatic; the helper can be exposed both as a callable and a `Depends`-compatible function. Prefer the plain callable inside handlers because several routes derive `guild_id` from `Form(...)` which is not available to a path-less dependency without extra wiring.
- Middleware that inspects path/form: rejected because `guild_id` lives in form bodies on several routes, which middleware cannot reliably read without consuming the body.

### 3. Treat `guild_id` as untrusted on every endpoint
Validate `guild_id` on read routes (`/api/music/status/{guild_id}`, `/api/music/queue/{guild_id}`), mutating routes (`/api/music/play`, `/controls/{action}`, `/volume`, `/repeat`, `/shuffle`, `/queue/remove`, `/queue/reorder`), the suggestions/sources routes that accept `guild_id`, and the WebSocket. The `/plugin/music` page itself is guild-agnostic (renders the picker); it only requires authentication.

### 4. Volume bounds: web aligns to 0-100, driven by config
Change the web `/api/music/volume` validation from `0 <= volume <= 150` to `0 <= volume <= 100`, and prefer reading the upper bound from the plugin's `max_volume` config (default 100) so the two surfaces cannot drift again. The Discord `/volume` command already enforces 0-100 and needs no change.

**Rationale:** The Discord command and `max_volume` config are the source of truth; the web panel was the outlier. Using the config value prevents a future re-drift.

### 5. Seek/position broadcast
After `player.seek(...)` in `/seek`, call the existing `_broadcast_music_update(plugin, ctx.guild_id, "playback_update")` helper used by the other playback commands. For `/position`, broadcast the same `playback_update` so the panel's progress bar resyncs (position is read-only but the panel polls/syncs on update events). Reuse the existing broadcast helper rather than inventing a new event type.

**Rationale:** Minimal change, consistent with how pause/resume/skip already sync the panel.

### 6. Previous track: implement via history
Implement previous-track using the existing per-guild history system (the `MusicEventHandler` already records history on `TrackStartEvent`, and history is queried elsewhere). The control plays the most recent history entry that is not the current track, prepends it to the queue, and broadcasts. If no usable history entry exists, return an informational "No previous track" response (not a stub).

**Rationale:** The history system already exists, so this delivers a working feature rather than removing UI. Removing the button was the alternative; chosen against because the panel already advertises the control and history makes it feasible.

**Alternatives considered:**
- Remove the button: simpler, but loses a user-facing control the panel UI implies.
- Build a separate undo stack: rejected as redundant with the existing history system.

### 7. Test strategy
Create `tests/unit/plugins/music/` with:
- `test_web_auth.py`: FastAPI `TestClient` against the plugin's router with a fake session; assert 401 unauthenticated, 403 for a guild not in the session guild list, 200/expected for an authorized guild, across the mutating and read routes.
- `test_web_volume.py`: assert values >100 are rejected and ≤100 are applied.
- `test_playback_broadcast.py`: mock the player and the broadcast helper; assert `/seek` and `/position` invoke the broadcast helper with `"playback_update"`.
- `test_previous_track.py`: assert history-backed previous-track plays the last entry and broadcasts, and the empty-history case returns the informational response.
- `test_commands_*`: light coverage for the existing command handlers (volume bounds, skip, pause/resume) to lift the plugin from zero coverage.

Reuse the async fixtures and plugin stubs in `tests/conftest.py`; add a music-plugin fixture that wires a fake `lavalink_client`/player and a session-backed request where needed.

## Risks / Trade-offs

- [Session guild list can go stale if the user leaves a guild after OAuth] → Mitigation: the panel already re-derives guilds on login; a stale entry only lets a former member see a guild they left until next login, and Discord-side the bot won't act in guilds it isn't in. Acceptable for a control panel; document the refresh-on-login expectation.
- [Form-body `guild_id` cannot be read by pure path middleware] → Mitigation: authorization runs inside each handler after form parsing (Decision 2), not in middleware.
- [Implementing previous-track adds a new code path with its own bugs] → Mitigation: reuse the existing history query logic and cover it with `test_previous_track.py`; keep the empty-history branch explicit.
- [Broadcasting on `/position` adds a message on a read-only command] → Mitigation: the event is the same `playback_update` the panel already handles; the cost is one extra WebSocket frame per `/position` invocation, acceptable for sync correctness.

## Migration Plan

1. Add the authorization helper and wire it into all routes + WebSocket (no behavior change for authorized users; unauthorized users now get 401/403 instead of control).
2. Fix the web volume bound to 0-100/config.
3. Add seek/position broadcasts.
4. Implement previous-track (or, if a follow-up audit prefers removal, remove the button in the same step).
5. Add the test suite; ensure `uv run pytest` and `make lint` pass.
6. Update the plugin README/AGENTS notes to document the per-guild authorization pattern as the reference for web-enabled plugins.

Rollback: each step is independently revertible; the authorization helper can be short-circuited to always-allow in an emergency without touching the other fixes.

## Open Questions

None — all decisions needed to start implementation are resolved above.
