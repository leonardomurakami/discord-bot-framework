## Context

The admin plugin already ships a polished permission-management web panel (`plugins/admin/web/routes.py` + `templates/panel.html`) backed by FastAPI routes guarded by `DiscordAuth`. Five other admin features — prefix, autorole, bot info, server info, and uptime/status — exist only as Discord slash/prefix commands in `commands/settings.py` and `commands/info.py`. The panel also has two correctness bugs: a hardcoded `"!"` default prefix when creating guild records (`routes.py` line 71) and inconsistent single-quote escaping using `chr(39)` (`routes.py` lines 234, 370) instead of the existing `escHtml()` helper defined in `panel.html`.

See `proposal.md` for motivation and scope.

## Goals / Non-Goals

**Goals:**
- Bring the five missing admin features to the web panel with behaviour parity to their Discord command counterparts.
- Reuse the data-gathering logic already present in the command modules so command and web surfaces cannot drift.
- Fix the default-prefix and XSS-escaping bugs in the existing routes.
- Establish test coverage for the previously untested command and web surfaces.

**Non-Goals:**
- Redesigning the existing permission management UI or its REST contract.
- Adding new Discord commands or changing command behaviour.
- Introducing new runtime dependencies (psutil remains optional).
- Real-time push updates (e.g. WebSocket/SSE) for the status view; it is read-only and refreshed on demand.

## Decisions

### Decision 1: Tabbed single-page panel instead of separate pages
The expanded panel keeps a single `/plugin/admin` entry point and organises features into client-side tabs (Permissions, Prefix, Auto Roles, Bot Info, Server Info, Status). The existing permission UI stays in its current tab; new tabs are added alongside it.

**Rationale:** The current panel already loads guild context once and swaps content via HTMX/JS. Tabs preserve that pattern, avoid a route explosion, and keep all admin features one click away. A sidebar was considered but rejected because it would require restructuring the existing template and would not add value at the current feature count.

**Alternatives considered:** Separate routes per feature (`/plugin/admin/prefix`, `/plugin/admin/autorole`, …) — rejected as heavier navigation and redundant guild-context loading.

### Decision 2: Extract shared data helpers from command modules
Prefix validation, autorole hierarchy validation, bot-overview gathering, guild summarisation, and uptime/status collection will be moved into small reusable functions (in `config.py` or a new `services.py`-style module) that both the command handlers and the web routes call.

**Rationale:** The commands already compute exactly the data the web views need (e.g. `plugin.bot.get_bot_overview()`, `plugin.bot.summarise_guild(guild)`, the prefix validation in `config.py`). Calling the same helpers from the routes guarantees parity and prevents the two surfaces from diverging. The autorole hierarchy check in particular must not be duplicated because getting it wrong is a security-relevant failure.

**Alternatives considered:** Duplicating the logic in the routes — rejected because of the drift risk, especially for hierarchy validation.

### Decision 3: REST endpoints follow the existing permission API conventions
New endpoints live under `/plugin/admin/api/guild/{guild_id}/...` and return JSON for state-changing operations and HTMX HTML fragments for list rendering, matching the existing roles/members/permissions endpoints. Auth gating reuses the existing `_require_guild_admin` helper.

- Prefix: `GET` (current value) and `POST /plugin/admin/api/guild/{guild_id}/prefix`.
- Autoroles: `GET /plugin/admin/api/guild/{guild_id}/autoroles`, `POST .../autoroles`, `DELETE .../autoroles/{role_id}`.
- Bot info: `GET /plugin/admin/api/bot-info`.
- Server info: `GET /plugin/admin/api/guild/{guild_id}/server-info`.
- Status: `GET /plugin/admin/api/status`.

**Rationale:** Consistency with the existing API shape keeps the front-end JS simple and the auth model uniform. Read-only info endpoints are not guild-admin-gated for bot info/status (they mirror the public `basic.admin.info.view`/`basic.admin.status.view` nodes) but still require authentication; server info and per-guild config endpoints remain guild-admin-gated.

**Alternatives considered:** A single aggregated `/api/guild/{id}/everything` endpoint — rejected as a coupling magnet that complicates caching and error handling per section.

### Decision 4: Role hierarchy validation in the web UI mirrors the command
The autorole add endpoint computes the bot's highest role position from the cached guild and rejects any target role at or above that position, returning a 400 with the same message the command uses. The front-end also disables/hides ineligible roles in the picker as a UX nicety, but the server check is authoritative.

**Rationale:** Client-side validation is convenience only; the server must enforce hierarchy because the cache can be stale and the API is directly callable. Reusing the command's helper avoids divergent rules.

### Decision 5: Configurable default prefix via `settings.bot_prefix`
`ensure_guild_exists` in `routes.py` will read `config.settings.settings.bot_prefix` instead of the hardcoded `"!"` when creating a `Guild` record.

**Rationale:** The global setting already exists (`config/settings.py` line 9) and is the source of truth for the prefix handler. Hardcoding `"!"` silently breaks guilds whose operator configured a different default.

### Decision 6: Consistent server-side escaping
The `chr(39)` substitutions in the roles and members HTML builders will be replaced with a shared escape helper (e.g. `html.escape` from the stdlib, or a small `esc_html` function in `routes.py`) applied to every user-supplied string interpolated into HTML. The client-side `escHtml()` in `panel.html` remains for JS-rendered content.

**Rationale:** `chr(39)` only strips single quotes (it does not even escape them), which both mangles role names and leaves angle-bracket XSS vectors open. A single server-side helper applied uniformly is correct and maintainable.

### Decision 7: Test strategy
Tests will be added under `tests/unit/plugins/admin/`:
- `test_prefix_command.py` — view/set/invalid cases using the existing command fixtures.
- `test_autorole_command.py` — add/remove/list/clear, duplicate, hierarchy violation, and on-join assignment (the latter via a fake `MemberCreateEvent`).
- `test_admin_web_routes.py` — FastAPI `TestClient` against a registered admin app stub, covering auth gating, prefix validation, autorole add/remove + hierarchy rejection, and the three read-only info endpoints (with and without psutil for status).
- `test_admin_views.py` — Miru pagination views: page next/prev, boundary, and empty-state rendering.

Web route tests will stub `DiscordAuth` and the Hikari cache the same way the existing `test_admin_plugin.py` does, to avoid live Discord/DB dependencies.

## Risks / Trade-offs

- **[Stale cache for hierarchy checks]** The bot's cached role positions can lag behind Discord. → Mitigation: the server-side check is authoritative and returns a clear 400; the front-end picker is best-effort only.
- **[Template growth]** Adding five tabs to `panel.html` increases its size. → Mitigation: keep each tab's markup in its own partial/section and reuse shared list/card components; accept the size as long as it stays a single template.
- **[psutil absence in CI]** Status tests that require psutil may be skipped where it is not installed. → Mitigation: parametrize the status test on psutil availability and assert the graceful-degradation path, mirroring the command's `ImportError` branch.
- **[Escaping helper drift]** Introducing a server-side `esc_html` alongside the client-side `escHtml` creates two helpers. → Mitigation: document that server-side escaping is for route-rendered HTML and client-side for JS-rendered HTML; both must escape quotes and angle brackets.

## Migration Plan

1. Extract shared helpers (prefix validation already in `config.py`; add autorole hierarchy, bot-overview, guild-summary, status wrappers if not already present).
2. Fix the default-prefix and escaping bugs in `routes.py` (small, low-risk; can ship independently).
3. Add the new REST endpoints and wire them to the shared helpers.
4. Add the new panel tabs and front-end JS in `panel.html`.
5. Add the test modules and confirm `uv run pytest tests/unit/plugins/admin` passes with coverage at or above the 70% threshold.

Rollback: each step is independently revertible. The bug fixes (step 2) are safe to ship first; the new tabs (step 4) are additive and can be hidden behind the existing auth without affecting the permission UI.

## Open Questions

None — all decisions needed to start implementation are resolved above.
