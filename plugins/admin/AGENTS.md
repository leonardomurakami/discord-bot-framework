# Admin Plugin Guidelines

## Overview
- Provides guild administration utilities: role permission management, prefix/autorole configuration, and rich telemetry about
  the bot and current guild.
- Powers the control panel at `/plugin/admin` with REST endpoints for viewing and editing permission assignments.
- Ships Miru pagination views to browse large permission sets directly inside Discord.
- Primary permission nodes: `admin.manage` for plugin-wide access, `admin.permissions.manage`, `admin.config.manage`,
  `admin.plugins.manage`, plus the public `basic.admin.info.view` and `basic.admin.status.view` nodes that expose telemetry
  commands to everyone by default.
- Optional dependency: [`psutil`](https://pypi.org/project/psutil/) enhances the uptime command with CPU/memory statistics.

## Architecture
- Package layout mirrors the standard plugin contract:
  - `plugin.py` exposes `AdminPlugin` (re-exported from `__init__.py`) and registers all commands during `_register_commands()`.
  - `commands/` holds the command factories:
    - `settings.py` → `/permission`, `/prefix`, `/autorole` (uses `admin.permissions.manage` and `admin.config.manage`).
    - `info.py` → informational commands (`/bot-info`, `/server-info`, `/uptime`).
  - `config.py` centralises embed colours, prefix validation rules, and feature mappings for server flags.
  - `views/__init__.py` defines Miru pagination components for listing permissions and role grants.
  - `web/` registers FastAPI routes for the admin panel (`web/routes.py`) and renders templates from `templates/panel.html`.
  - `models/` is currently empty but reserved for future admin-specific persistence.
- The plugin inherits both `BasePlugin` (command/setting helpers) and `WebPanelMixin` (panel registration) from the framework.
- Autorole membership and other lightweight settings are stored via `BasePlugin.get_setting`/`set_setting` in the shared database.

## Commands
| Command | Description | Permission Node | Notes |
| --- | --- | --- | --- |
| `/permission [action] [role] [permission]` | List, grant, or revoke permission nodes for a role. Supports wildcards and pagination. | `admin.permissions.manage` | The default action is `list`. Wildcards (`moderation.*`, `*.queue.manage`) are resolved through the `PermissionManager`. |
| `/prefix [new_prefix]` | View or update the guild prefix used by the prefix command handler. | `admin.config.manage` | Enforces `PREFIX_MAX_LENGTH` (5) and disallows quotes/backticks/whitespace defined in `config.py`. |
| `/autorole <add/remove/list/clear> [role]` | Configure roles automatically applied to new members. | `admin.config.manage` | Stored per guild via plugin settings; validates role hierarchy before assignment. |
| `/bot-info` (`/info`) | Displays guild count, plugin count, database status, and bot metadata. | `basic.admin.info.view` | `basic.` nodes are implicitly granted to everyone; psutil enhances the output when installed. |
| `/server-info` | Rich guild breakdown with counts, features, and artwork. | `basic.admin.info.view` | Pulls feature labels from `SERVER_FEATURE_MAPPING`; granted to all members by default. |
| `/uptime` (`/status`) | Shows bot uptime, start time, process metrics, and host statistics. | `basic.admin.status.view` | Also public via the `basic.` prefix; falls back gracefully when `psutil` is missing. |

## Configuration
- No dedicated environment variables; the plugin relies on the global `config.settings` for database access and general bot
  configuration.
- `config.py` exposes validation helpers:
  - `PREFIX_MAX_LENGTH` (default 5 characters).
  - `PREFIX_DISALLOWED_CHARS` (quotes, backticks, whitespace control characters).
  - `AUTOROLE_VALID_ACTIONS` to validate autorole sub-commands.
  - Colour constants reused by embeds.
- Autorole data is persisted as a list of role IDs under the key `"autoroles"` in the shared plugin settings table.
- The web panel relies on the global FastAPI app registered through `WebPanelMixin`. No extra configuration is required beyond the
  global web settings (host/port/secret) handled by the framework.

## Development Guidelines
- Keep new commands inside `commands/` modules; each factory should return decorated coroutine functions that `AdminPlugin` attaches
  during `_register_commands()`.
- Use `BasePlugin.smart_respond` for responses that should adapt to slash vs prefix invocations.
- Wrap database access in `async with plugin.bot.db.session():` blocks and commit within the context.
- The permission panel expects `Permission.description` and `Permission.category` fields to be populated; when adding new admin
  permissions ensure metadata includes friendly descriptions.
- Run focused tests after changes: `uv run pytest tests/unit/plugins/admin`.
- Web panel changes should maintain parity with the REST helpers in `web/routes.py`; keep JSON responses stable because the front-end
  JavaScript in `templates/panel.html` consumes them directly.

## Troubleshooting
- **Permission not appearing in panel:** restart the bot or call `permission refresh` (admin command) to trigger `PermissionManager`
  discovery. Ensure the command metadata includes `permission_node`.
- **Pagination buttons unresponsive:** check that the global Miru client is initialised (`DiscordBot` attaches it on startup). The
  view will log an error if `miru_client` is missing.
- **Prefix changes failing:** validate against `PREFIX_MAX_LENGTH` and confirm the database user has write access.
- **Autorole assignment fails on join:** confirm the bot role sits above the target role; the command already prevents misconfiguration
  but manual database edits can still break hierarchy expectations.

## Examples
### Add a scoped admin command
```python
from bot.plugins.commands import command

@command(
    name="reload-config",
    description="Reload external configuration",  # Describe the behaviour clearly
    permission_node="admin.plugins.manage",
)
async def reload_config(ctx: lightbulb.Context) -> None:
    plugin = ctx.app.get_plugin("admin")  # type: ignore[attr-defined]
    await plugin.bot.reload_configuration()
    await plugin.smart_respond(ctx, "Configuration reloaded.")
```

### Fetch role permissions from the web panel API
```python
# GET /plugin/admin/api/guild/{guild_id}/role/{role_id}/permissions
response = await http_client.get(
    "https://your-panel.example/api/plugin/admin/api/guild/123456789/role/987654321/permissions",
    headers={"Authorization": f"Bearer {token}"},
)
permissions = response.json()["permissions"]
```

Use these patterns to keep new features consistent with the rest of the plugin.
