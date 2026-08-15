## 1. Web Panel Guild Authorization

- [x] 1.1 Add an async `assert_guild_access(request, guild_id)` helper in `plugins/music/web/routes.py` that returns the authenticated user from `DiscordAuth.get_current_user(request)` and raises `HTTPException(401)` when unauthenticated or `HTTPException(403)` when `guild_id` is not in `request.session["guilds"]`
- [x] 1.2 Wire `assert_guild_access` into every read route (`/api/music/status/{guild_id}`, `/api/music/queue/{guild_id}`, `/api/music/queue`, `/api/music/search/suggestions`, `/api/music/sources`) before returning guild data
- [x] 1.3 Wire `assert_guild_access` into every mutating route (`/api/music/play`, `/api/music/controls/{action}`, `/api/music/volume`, `/api/music/repeat`, `/api/music/shuffle`, `/api/music/queue/remove`, `/api/music/queue/reorder`) before applying any control
- [x] 1.4 In the `/ws/music/{guild_id}` handler, run the authorization check before `websocket.accept()`; close unauthenticated/unauthorized connections with policy-violation code 1008 without sending music state
- [x] 1.5 Require authentication (but not a specific guild) on the `/plugin/music` page render

## 2. Volume Bounds Consistency

- [x] 2.1 Change `/api/music/volume` validation in `plugins/music/web/routes.py` from `0 <= volume <= 150` to `0 <= volume <= 100`, sourcing the upper bound from the plugin's `max_volume` config (default 100)
- [x] 2.2 Verify the `/volume` Discord command in `plugins/music/commands/voice.py` already enforces 0-100 and needs no change; confirm no other surface allows >100

## 3. WebSocket Sync for Seek and Position

- [x] 3.1 In `plugins/music/commands/playback.py`, after `player.seek(...)` in the `/seek` handler, call `_broadcast_music_update(plugin, ctx.guild_id, "playback_update")`
- [x] 3.2 In the `/position` handler, broadcast `playback_update` via `_broadcast_music_update` after computing the position so the panel resyncs

## 4. Previous-Track Control

- [x] 4.1 Implement the `previous` action in `/api/music/controls/{action}` using the existing per-guild history system: play the most recent history entry that is not the current track, prepend to the queue, save queue, and broadcast an update
- [x] 4.2 Return an informational "No previous track available" response (not a stub) when no usable history entry exists
- [x] 4.3 Update `plugins/music/web/templates/panel.html` and any queue/controls JS so the previous-track button reflects the implemented behavior (remove the stub comment/label)

## 5. Tests

- [x] 5.1 Create `tests/unit/plugins/music/` and add a music-plugin fixture in `tests/conftest.py` (or a local conftest) wiring a fake `lavalink_client`/player and a session-backed request
- [x] 5.2 Add `test_web_auth.py` asserting 401 unauthenticated, 403 for a guild not in the session guild list, and success for an authorized guild across read and mutating routes
- [x] 5.3 Add `test_web_volume.py` asserting values >100 are rejected and values within 0-100 are applied
- [x] 5.4 Add `test_playback_broadcast.py` mocking the player and broadcast helper to assert `/seek` and `/position` broadcast `playback_update`
- [x] 5.5 Add `test_previous_track.py` covering the history-backed previous-track path and the empty-history informational response
- [x] 5.6 Add `test_commands_*.py` with light coverage for existing command handlers (volume bounds, skip, pause/resume) to lift the plugin from zero coverage

## 6. Validation and Docs

- [x] 6.1 Run `uv run pytest tests/unit/plugins/music` and `uv run ruff check .` and fix any failures
- [x] 6.2 Run `openspec validate music-panel-hardening` and confirm the change validates
- [x] 6.3 Update the music plugin README/AGENTS notes to document the per-guild web authorization pattern as the reference for `WebPanelMixin` plugins
