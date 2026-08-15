## Why

The music plugin's web panel exposes 14 routes and a WebSocket with no per-guild authorization: any authenticated panel user can control any guild's music by supplying an arbitrary `guild_id` in form data, and several behaviors (volume range, seek/position sync, the previous-track button) are inconsistent or stubbed. As the framework's reference web-panel implementation, these gaps are both a security hole and a poor example for plugin authors.

## What Changes

- Add per-request guild authorization to every music web route and WebSocket endpoint: validate that the authenticated user is a member of the guild identified by the supplied `guild_id`, rejecting requests for guilds the user does not belong to.
- Treat `guild_id` as untrusted input: derive/validate it against the session's Discord guild list on every mutating and read endpoint, and reject mismatches with a 403.
- Fix the volume range mismatch so the web panel enforces the same 0-100 bounds as the `/volume` Discord command (web currently allows 0-150).
- Broadcast a WebSocket update when `/seek` and `/position` run so the web panel stays in sync after Discord-side seek/position actions.
- Resolve the stubbed "Previous track" web control: either implement it using the existing history system or remove the button from the panel UI so users never see a dead control.
- Add the first unit-test suite for the music plugin covering commands and web routes, including authorization, volume bounds, and WebSocket broadcast behavior.

## Capabilities

### New Capabilities

None — this modifies an existing capability.

### Modified Capabilities

- `plugins/music`: Web panel routes now require per-guild authorization and treat `guild_id` as untrusted; volume bounds are consistent across web and Discord; seek/position commands broadcast WebSocket updates; previous-track behavior is defined (implemented or removed); test coverage is added for commands and web routes.

## Impact

- **Affected code**: `plugins/music/web/routes.py` (all routes + WebSocket endpoint authorization and volume bounds), `plugins/music/commands/playback.py` (seek/position WebSocket broadcast), `plugins/music/commands/voice.py` (volume bounds already 0-100; web side aligned to it), `plugins/music/web/templates/panel.html` (previous-track button removal or wiring), `plugins/music/web/static/` (queue/controls JS if previous track is implemented).
- **APIs**: Music web REST endpoints (`/api/music/*`) and WebSocket (`/ws/music/{guild_id}`) gain a 403 response path for unauthorized guild access; no successful-response shape changes.
- **Dependencies**: Relies on the existing `DiscordAuth` session (`request.session["guilds"]`) for the user's guild list — no new external dependencies.
- **Tests**: New `tests/unit/plugins/music/` directory with command and web-route tests; fixtures extended as needed in `tests/conftest.py`.
- **Docs**: Update plugin README/AGENTS notes to document the per-guild authorization pattern as the reference for web-enabled plugins.
