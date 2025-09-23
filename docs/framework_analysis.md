# Framework Accessor and Pattern Analysis

## Current Accessor Patterns
### Aggregated View
- Repeated access to bot subsystems is heavily skewed toward database sessions and Discord client interactions. `plugin.bot.db.session` appears six times across plugins, while `music_plugin.bot.db.session` contributes another five usages dedicated to queue persistence routines.【ecaaab†L1-L26】
- Command discovery and help flows depend on the message handler and plugin loader: patterns such as `self.bot.message_handler.commands.items` and `self.bot.plugin_loader.get_plugin_info` each surface four times inside the help plugin’s embed generators.【ecaaab†L12-L22】【F:plugins/help/views/embed_generators.py†L74-L156】
- Music commands lean on nested `ctx.bot.hikari_bot.*` calls (voice state checks, REST fetches) five or more times per method, reflecting the lack of a convenience layer around gateway state.【ecaaab†L4-L11】【F:plugins/music/commands/playback.py†L30-L159】

### Plugin Highlights
- **Admin** – Status commands call into multiple subsystems: guild counts from `hikari_bot.cache`, database health checks, and plugin loader introspection.【F:plugins/admin/commands/info.py†L34-L69】 Web routes gate access through `plugin.bot.web_panel_manager.web_app.auth`, producing long attribute chains before reaching the auth helper.【F:plugins/admin/web/routes.py†L103-L141】
- **Help** – Embed generation walks both the message handler map and plugin loader metadata on every request, leading to repeated `self.bot.message_handler.*` and `self.bot.plugin_loader.*` calls.【F:plugins/help/views/embed_generators.py†L74-L156】
- **Links** – Each command enters `async with self.plugin.bot.db.session()` to fetch or mutate rows, often followed by `create_embed`/`smart_respond` blocks for feedback.【F:plugins/links/commands/link_commands.py†L40-L215】
- **Moderation** – Enforcement actions call Lightbulb contexts plus Hikari REST helpers like `plugin.bot.hikari_bot.rest.fetch_user`, interleaving embed creation and `smart_respond`/`log_command_usage` pairs for success and failure paths.【F:plugins/moderation/commands/actions.py†L130-L252】
- **Music** – Playback logic uses `ctx.bot.hikari_bot` for voice/channel state and `music_plugin.bot.db.session()` for queue persistence, mixing gateway, Lavalink, and ORM access within the same functions.【F:plugins/music/commands/playback.py†L30-L159】【F:plugins/music/utils.py†L14-L220】
- **Utility/Fun** – Both plugins mirror the moderation pattern: frequent `create_embed` and `smart_respond` usage with post-command analytics via `log_command_usage`, despite minimal database access (settings or cached data only).【aa98f7†L1-L17】

## Redundant/Awkward Patterns
- **Double bot attribute** – `CommandRegistry` registers slash commands through `self.bot.bot.register(...)`, exposing the Lightbulb client via a second `bot` attribute on `DiscordBot` instead of a dedicated accessor.【F:bot/plugins/commands/registry.py†L140-L152】【F:bot/core/bot.py†L20-L48】
- **Deep web panel lookup** – Admin web routes guard FastAPI handlers with `plugin.bot.web_panel_manager.web_app.auth`, a four-step chain that repeats across endpoints and requires defensive `hasattr` checks.【F:plugins/admin/web/routes.py†L103-L139】
- **Discord cache fan-out** – Stats commands repeatedly touch `plugin.bot.hikari_bot.cache.get_guilds_view()` and similar cache helpers, suggesting a higher-level façade for guild summaries could replace direct cache traversal.【F:plugins/admin/commands/info.py†L34-L59】
- **Voice utilities in music commands** – Patterns like `ctx.bot.hikari_bot.update_voice_state`/`cache.get_voice_state` appear multiple times per command, mixing context plumbing with playback logic.【F:plugins/music/commands/playback.py†L30-L147】【ecaaab†L4-L11】

## Common Operations
- **Embeds and responses** – Plugins call `create_embed` 240 times and `smart_respond` 221 times across the tree, typically as adjacent statements inside each command handler.【aa98f7†L1-L17】 Moderation and music modules exemplify the pattern by constructing embeds for every branch before routing replies through `smart_respond`.【F:plugins/moderation/commands/actions.py†L130-L252】【F:plugins/music/commands/playback.py†L30-L159】
- **Command analytics** – `log_command_usage` fires 104 times, usually immediately after responding, duplicating the `await plugin.log_command_usage(..., success, error)` shape across plugins that track moderation and utility actions.【aa98f7†L9-L17】
- **Settings persistence** – `get_setting`/`set_setting` pairs appear nine times, mainly within moderation warnings and admin configuration flows, demonstrating a shared need for per-guild key/value helpers.【aa98f7†L17-L24】【F:plugins/moderation/commands/discipline.py†L37-L154】
- **Database sessions** – `bot.db.session()` contexts are concentrated in links and music (six and five usages respectively), each following the same `async with ... session()` → `select/execute` → `commit` structure.【1450d3†L1-L8】【F:plugins/links/commands/link_commands.py†L40-L215】【F:plugins/music/utils.py†L14-L220】
- **Discord client access** – Forty-two references to `bot.hikari_bot` span admin telemetry, help embeds, music commands, and utility lookups, emphasising how frequently plugins reach into the low-level gateway client for cache, REST, or voice helpers.【2a2a5c†L1-L8】【F:plugins/admin/commands/info.py†L34-L59】【F:plugins/music/commands/playback.py†L30-L147】

## Refactoring Proposals
### BasePlugin Enhancements
- **Cached service shortcuts** – Attach cached properties (`self.db`, `self.permissions`, `self.events`, `self.web_panel`) in `BasePlugin.__init__` so commands can reference `self.db.session()` or `self.permissions` directly, eliminating long chains like `plugin.bot.permission_manager` and `self.bot.db.session`. This mirrors the existing pattern where `BasePlugin` already exposes `self.logger` and `self.name` for convenience.【F:bot/plugins/base.py†L13-L77】【F:plugins/admin/commands/settings.py†L61-L135】
- **Discord helpers** – Provide wrappers such as `self.fetch_user(user_id)` and `self.update_voice_state(guild_id, channel_id)` that delegate to the Hikari client, reducing repeated `ctx.bot.hikari_bot` lookups in music commands.【F:plugins/music/commands/playback.py†L30-L147】
- **Response macros** – Add composite helpers (`respond_success`, `respond_error`) that build embeds and call `smart_respond` internally, consolidating the recurring embed + respond + log triads in moderation and utility workflows.【F:plugins/moderation/commands/actions.py†L130-L252】【F:plugins/utility/commands/info.py†L40-L120】

### Core Framework Improvements
- **Expose explicit clients** – Rename or alias `DiscordBot.bot` to `command_client` (or similar) and surface property methods for `rest`, `cache`, and `voice` operations, avoiding nested `self.bot.bot` and `ctx.bot.hikari_bot` access throughout the codebase.【F:bot/core/bot.py†L20-L89】【F:bot/plugins/commands/registry.py†L140-L152】
- **Service façade** – Provide a lightweight service registry on `DiscordBot` (e.g., `self.services["db"]`) so plugins can request dependencies without touching private attributes, reducing the need for `hasattr` checks before using `web_panel_manager.web_app.auth`.【F:bot/core/bot.py†L34-L129】【F:plugins/admin/web/routes.py†L103-L139】
- **Guild summary API** – Add helper methods to `DiscordBot` (or a new utility module) for guild statistics, abstracting repeated cache access for counts and enabling caching or memoisation strategies later.【F:plugins/admin/commands/info.py†L34-L59】

### New Auxiliary Functions
- **Database helpers** – Implement context-managed helpers such as `BasePlugin.with_session(callback, *, commit=True)` that wrap `async with self.db.session()` and centralise error logging, cutting duplicate session boilerplate in links/music persistence flows.【F:plugins/links/commands/link_commands.py†L40-L215】【F:plugins/music/utils.py†L14-L220】
- **Event publisher guard** – Supply an `emit_event` helper that logs failures and optionally swallows exceptions, simplifying the try/except scaffolding around `event_system.emit` that plugins would otherwise copy when broadcasting state changes.【F:bot/core/event_system.py†L34-L99】
- **Bulk permission checks** – Provide a `PermissionManager.check_members(guild_id, members, node)` helper returning authorised IDs, replacing manual iteration when moderation commands need to validate multiple targets against the same node.【F:plugins/moderation/commands/actions.py†L130-L252】
- **Standard analytics hook** – Offer a decorator or context manager (`with plugin.track_command(ctx, name) as tracker:`) that records success/failure automatically, reducing the repeated `try`/`except` → `log_command_usage` pattern that currently occurs over 100 times.【aa98f7†L9-L17】【F:plugins/moderation/commands/actions.py†L130-L252】

## Implementation Plan
1. **Phase 1 – Introduce opt-in helpers**
   - Add cached service properties and auxiliary methods to `BasePlugin` plus façade properties on `DiscordBot` without altering existing attributes. Provide deprecation warnings (via logging) when legacy chains are used in new helpers to ease migration.【F:bot/plugins/base.py†L13-L198】【F:bot/core/bot.py†L20-L129】
2. **Phase 2 – Migrate plugins**
   - Update first-party plugins to rely on the new helpers (`self.db`, `self.permissions`, response macros) module by module, verifying behaviour through existing tests. Keep backward compatibility by leaving the old accessors in place during the migration window.【F:plugins/links/commands/link_commands.py†L40-L215】【F:plugins/music/commands/playback.py†L30-L159】
3. **Phase 3 – Deprecate legacy patterns**
   - Emit structured warnings for direct `self.bot.bot`, `plugin.bot.db.session`, and other long chains, documenting preferred replacements in the new `bot/core/AGENTS.md` reference and changelog entries.【F:bot/plugins/commands/registry.py†L140-L152】【F:bot/core/AGENTS.md†L1-L72】
4. **Phase 4 – Remove deprecated code**
   - After plugins adopt the helpers, delete compatibility shims and redundant `hasattr` guards, tightening type hints around the new façade methods and ensuring tests cover the streamlined APIs.【F:plugins/admin/web/routes.py†L103-L139】【F:bot/plugins/base.py†L13-L198】
