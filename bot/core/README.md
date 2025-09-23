# Bot Core Framework Overview

The core package orchestrates every subsystem that powers the Discord bot. It wires together the Discord clients, database, permissions, web panel, and plugin loader so plugin authors can focus on feature logic.

## Responsibilities of `DiscordBot`

`bot/core/bot.py` defines `DiscordBot`, the runtime coordinator. Its main duties are:

- Construct the gateway, slash command, and component clients (Hikari, Lightbulb, Miru).
- Expose framework services (database manager, permission manager, plugin loader, event system, web panel) through a shared registry.
- Bootstrap the bot on startup: create database tables, initialise permissions, load enabled plugins, and launch the web panel.
- Relay Discord events to the custom prefix handler and the internal `EventSystem`.
- Provide lifecycle hooks for shutdown so plugins and background tasks can clean up safely.

The bot is launched by the CLI (`python -m bot` or `bot/cli.py run`) which constructs a single `DiscordBot` instance and calls `run()`.

## Startup lifecycle

1. **Constructor** (`__init__`)
   - Creates the Hikari `GatewayBot`, Lightbulb app, and Miru client.
   - Installs permission decorators so the `PermissionManager` can inspect the bot instance.
   - Instantiates core services: `db_manager`, `EventSystem`, `MessageCommandHandler`, `PluginLoader`, `PermissionManager`, and `WebPanelManager`.
   - Registers each service inside `self.services` using `_register_core_services()`.
   - Seeds plugin directories from `config.settings.settings.plugin_directories`.
   - Subscribes to key gateway events via `_setup_event_listeners()`.

2. **Event driven initialisation**
   - When Hikari fires `StartedEvent`, `_initialize_systems()` runs:
     - Create database tables via `DatabaseManager.create_tables()`.
     - Attach and initialise `PermissionManager`.
     - Discover and load plugins listed in `settings.enabled_plugins`.
     - Refresh permissions now that plugin metadata is known.
     - Start the FastAPI control panel through `WebPanelManager.start()`.
     - Execute any registered startup tasks (see `add_startup_task`).
   - `ShardReadyEvent` emits the `bot_ready` event once, signalling to plugins that all systems are online.

3. **Shutdown**
   - `StoppingEvent` triggers `_cleanup()` which emits `bot_stopping`, stops the web panel, unloads plugins, and closes the database connection.

## Service registry

Plugins can reach shared infrastructure through either cached attributes on `BasePlugin` or by looking up names in the service registry. The default registry entries are:

| Key              | Object                                  | Usage |
| ---------------- | ---------------------------------------- | ----- |
| `gateway`        | `hikari.GatewayBot`                      | Raw Discord gateway client (REST, cache, voice). |
| `command_client` | `lightbulb.Client`                       | Slash and application command router. |
| `miru`           | `miru.Client`                            | Component and view handling. |
| `db`             | `DatabaseManager`                        | Async SQLAlchemy engine, sessions, and model registry. |
| `events`         | `EventSystem`                            | Publish/subscribe bus for framework events. |
| `message_handler`| `MessageCommandHandler`                  | Prefix command routing and permission enforcement. |
| `plugin_loader`  | `PluginLoader`                           | Discovers, loads, reloads, and unloads plugin packages. |
| `permissions`    | `PermissionManager`                      | Role-based permission store and helper APIs. |
| `web_panel`      | `WebPanelManager`                        | FastAPI web UI, OAuth, and static asset mounting. |

Call `register_service(name, service)` to expose custom objects (for example, a shared HTTP client) and `get_service(name)` to retrieve them later.

## Major subsystems

### Event system

`bot/core/event_system.py` implements an async publish/subscribe hub. Plugins register handlers with `@event_listener('event_name')`, and `BasePlugin` manages registration during load/unload. Middleware can be attached with `EventSystem.add_middleware()` to observe or cancel events.

### Plugin loader

`PluginLoader` discovers plugin packages from configured directories, validates metadata, and instantiates subclasses of `BasePlugin`. It exposes helpers to load, unload, and reload plugins at runtime which the admin tooling uses.

### Message command handler

`MessageCommandHandler` routes prefix commands. It inspects messages for the configured prefix, resolves a `PrefixContext`, enforces permission nodes, and executes the associated callback registered by the command decorators.

### Permission manager

`PermissionManager` initialises from the database and plugin metadata to provide hierarchical permission checks. Plugins can query `has_permission`, grant or revoke nodes, and enumerate guild level permissions via the cached reference in `BasePlugin`.

### Web panel

`WebPanelManager` hosts the FastAPI admin panel, wiring templates, static assets, and plugin contributed routes. Plugins integrate through `WebPanelMixin`, and the manager starts automatically during bot initialisation.

### Database manager

`DatabaseManager` (imported as `db_manager`) configures the async SQLAlchemy engine, creates tables, and exposes an async session context manager used by `BasePlugin.db_session()`.

## Convenience APIs for plugins and tooling

`DiscordBot` offers several helper properties and methods that plugins rely on:

- `command_client` property for Lightbulb. The legacy `bot` alias still exists but emits a deprecation warning.
- `gateway`, `rest`, and `cache` properties mirror the underlying Hikari client for convenience.
- `add_startup_task(coro)` schedules an async callable to run after core systems initialise.
- `get_bot_overview()` returns a snapshot (`BotOverview`) with the current bot user, guild count, loaded plugin count, and database health.
- `summarise_guild(guild)` builds a `GuildSummary` containing channel, role, emoji, and member metrics for dashboards.
- `get_guild_prefix(guild_id)` reads the per guild prefix from the database, falling back to the global default.

These helpers are surfaced to plugins through `BasePlugin` (for example, `BasePlugin.get_guild_prefix`) to keep feature code concise.

## Extending the core

- **Custom services**: call `register_service` during startup (for example in a plugin's `on_load`) to add reusable clients. Existing plugins can later call `self.bot.get_service('my_service')`.
- **Additional event hooks**: subscribe directly to `gateway.listen(...)` for raw Discord events or emit new `EventSystem` events for cross plugin communication.
- **Startup coordination**: plugins that need to run work after the core is ready can pass coroutines to `add_startup_task` during `on_load`.

## Testing and diagnostics

Unit tests in `tests/unit/bot/` exercise the bot core (`test_bot_core.py`), event system, and base plugin utilities. Use them as references when extending behaviour or adding new helpers. The command handler and plugin loader each have targeted fixtures that demonstrate how to instantiate the bot in isolation.

For runtime diagnostics, `get_bot_overview()` pairs with the admin plugin to render status pages, while `summarise_guild()` supports guild dashboards.
