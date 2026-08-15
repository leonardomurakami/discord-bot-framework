## 1. Shared helpers and bug fixes

- [x] 1.1 Replace the hardcoded `"!"` default prefix in `plugins/admin/web/routes.py` `ensure_guild_exists` with `config.settings.settings.bot_prefix`.
- [x] 1.2 Add a shared server-side HTML escape helper (e.g. `esc_html` using `html.escape`) in `plugins/admin/web/routes.py` and replace the `chr(39)` substitutions on lines 234 and 370 with calls to it, escaping all user-supplied role/member name values interpolated into HTML.
- [x] 1.3 Extract prefix validation into a reusable function (length, empty/whitespace, disallowed chars) in `plugins/admin/config.py` and refactor `commands/settings.py` `manage_prefix` to call it.
- [x] 1.4 Extract the autorole role-hierarchy check into a reusable async helper (returns bot top role position vs target role) and refactor `commands/settings.py` `autorole` to call it.

## 2. Web panel data endpoints

- [x] 2.1 Add `GET /plugin/admin/api/guild/{guild_id}/prefix` returning the current guild prefix (guild-admin gated).
- [x] 2.2 Add `POST /plugin/admin/api/guild/{guild_id}/prefix` that validates via the shared prefix helper, updates the Guild record, and returns JSON; returns 400 on invalid input and 401/403 on auth failure.
- [x] 2.3 Add `GET /plugin/admin/api/guild/{guild_id}/autoroles` returning the configured autoroles with resolved role names (HTMX HTML or JSON, matching existing conventions).
- [x] 2.4 Add `POST /plugin/admin/api/guild/{guild_id}/autoroles` that validates hierarchy via the shared helper, rejects duplicates, persists the role ID, and returns JSON.
- [x] 2.5 Add `DELETE /plugin/admin/api/guild/{guild_id}/autoroles/{role_id}` that removes the role ID and returns JSON.
- [x] 2.6 Add `GET /plugin/admin/api/bot-info` returning bot overview data (auth required, not guild-admin gated).
- [x] 2.7 Add `GET /plugin/admin/api/guild/{guild_id}/server-info` returning the guild summary (guild-admin gated) with a clear empty state when the guild is uncached.
- [x] 2.8 Add `GET /plugin/admin/api/status` returning uptime/status data, degrading gracefully when psutil is missing (auth required).

## 3. Web panel UI

- [x] 3.1 Add tab/section navigation to `plugins/admin/templates/panel.html` with Permissions as the default tab and tabs for Prefix, Auto Roles, Bot Info, Server Info, and Status.
- [x] 3.2 Implement the Prefix tab: shows current prefix, a form to set a new prefix, validation error display, and success toast — calling the prefix endpoints via HTMX/JS.
- [x] 3.3 Implement the Auto Roles tab: lists current autoroles, provides add (role picker) and remove buttons, disables ineligible roles client-side, and shows hierarchy/duplicate errors from the API.
- [x] 3.4 Implement the Bot Info tab as a read-only card rendering the `/bot-info` data.
- [x] 3.5 Implement the Server Info tab as a read-only card rendering the `/server-info` data, including icon/banner and an empty state for uncached guilds.
- [x] 3.6 Implement the Status tab as a read-only card rendering the `/uptime` data, with a psutil-absent note when metrics are unavailable.

## 4. Tests

- [x] 4.1 Add `tests/unit/plugins/admin/test_prefix_command.py` covering view current prefix, set valid prefix, and reject too-long/empty/disallowed-char prefixes.
- [x] 4.2 Add `tests/unit/plugins/admin/test_autorole_command.py` covering add, remove, list, clear, duplicate-add, hierarchy-violation rejection, and automatic role assignment on member join.
- [x] 4.3 Add `tests/unit/plugins/admin/test_admin_web_routes.py` covering auth gating, prefix get/set + validation errors, autorole add/remove + hierarchy rejection, and the bot-info/server-info/status endpoints (status tested with and without psutil).
- [x] 4.4 Add `tests/unit/plugins/admin/test_admin_views.py` covering Miru permission and role-permission pagination views: next/prev navigation, boundary pages, and empty states.
- [x] 4.5 Run `uv run pytest tests/unit/plugins/admin --cov=plugins/admin` and confirm the suite passes with coverage at or above 70%.

## 5. Validation

- [x] 5.1 Run `uv run ruff check .` and `uv run black --check .` and fix any issues in changed files.
- [ ] 5.2 Manually verify the panel in a dev bot session (`make bot-dev`): load each tab, set a prefix, add/remove an autorole, and confirm the info/status tabs render.
- [x] 5.3 Run `openspec validate admin-panel-parity --strict` and resolve any reported spec issues.
