## Why
The admin plugin's web panel is excellent for permission management (role + user permissions, wildcards, bulk actions, search, categories) but is missing every other admin feature that already exists as Discord commands — prefix management, autorole management, bot info, server info, and uptime/status. Because the framework is the product, the admin panel should be a complete administrative interface, not a permissions-only tool. Two bugs also undermine the panel's correctness: a hardcoded default prefix `"!"` that ignores the configured global default, and inconsistent XSS escaping that uses ad-hoc `chr(39)` substitutions instead of the existing `escHtml()` helper.

## What Changes
- Add a web UI for prefix management: a form to view and set the guild prefix, reusing the same validation rules as the `/prefix` command (max 5 chars, no quotes/backticks/whitespace).
- Add a web UI for autorole management: a list of current autoroles with add/remove buttons, including role hierarchy validation (bot must be above the target role) before allowing an add.
- Add a read-only bot info view to the panel that surfaces guild count, plugin count, database status, and bot metadata (equivalent to `/bot-info`).
- Add a read-only server info view to the panel that surfaces server ID, owner, creation date, member/channel/role/emoji counts, features, and icon/banner (equivalent to `/server-info`).
- Add a read-only uptime/status view to the panel that surfaces bot uptime, start time, memory/CPU (when psutil is available), server count, gateway latency, and PID (equivalent to `/uptime`).
- Fix the hardcoded default prefix `"!"` in `routes.py` so guild records are created using the global config default (`settings.bot_prefix`).
- Replace the inconsistent `chr(39)` single-quote escaping in `routes.py` with the existing `escHtml()` helper (or an equivalent server-side escape) for all user-supplied values rendered into HTML.
- Add tests covering the prefix command, autorole command (including hierarchy validation and on-join assignment), the web panel routes (prefix, autorole, info, status), and the Miru pagination views.

## Capabilities

### New Capabilities
None — this modifies an existing capability.

### Modified Capabilities
- `plugins/admin`: Add web panel parity requirements for prefix management, autorole management, bot info, server info, and uptime/status views; require consistent XSS escaping and a configurable default prefix; add test coverage requirements for the previously untested command and web surfaces.

## Impact
- **Affected code:**
  - `plugins/admin/web/routes.py` — new routes for prefix, autorole, bot info, server info, and uptime; bug fixes for default prefix and XSS escaping.
  - `plugins/admin/templates/panel.html` — new UI sections (tabs/sections) for the added features; reuse of `escHtml()`.
  - `plugins/admin/config.py` — may expose shared helpers (e.g., prefix validation) reused by both command and web surfaces.
  - `plugins/admin/commands/settings.py` and `commands/info.py` — extract data-gathering logic so the web panel can reuse it without duplicating command code.
- **APIs:** New REST endpoints under `/plugin/admin/api/guild/{guild_id}/...` for prefix and autorole, plus read-only endpoints for bot info, server info, and status. Existing permission endpoints are unchanged.
- **Dependencies:** No new runtime dependencies; psutil remains optional and the status view degrades gracefully when it is absent.
- **Tests:** New test modules under `tests/unit/plugins/admin/` for prefix, autorole, web routes, and Miru views; existing tests remain valid.
