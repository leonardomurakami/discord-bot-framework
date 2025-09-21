# Agent Handbook for `discord-bot-framework`

Welcome! This repository houses a modular Discord bot built on top of Hikari (gateway client), Lightbulb (command router), and Miru (component UI). Plugins drive all user-facing features, while shared services cover persistence, permissions, and event orchestration. Use this guide to stay aligned with the existing architecture.

## 1. High-level picture
1. `python -m bot` or `bot/cli.py run` constructs `bot.core.bot.DiscordBot`.
2. `DiscordBot` wires together the Hikari gateway client, the Lightbulb command client, Miru UI, the async SQLAlchemy database manager, the permission subsystem, the plugin loader, the event system, and the custom prefix command handler.
3. During startup `_initialize_systems()` creates tables, seeds default permissions, loads enabled plugins from `config.settings.settings.enabled_plugins`, then announces readiness through the internal `EventSystem`.
4. Plugins register slash and prefix commands via the unified decorators in `bot.plugins.commands`, hook into events with `bot.core.event_system.event_listener`, and use helpers from `bot.plugins.base.BasePlugin` for embeds, logging, and persistence.

## 2. Repository tour
- `bot/__main__.py` – CLI-friendly entry point that configures logging and starts the gateway bot.
- `bot/cli.py` – Typer-based CLI for running the bot, scaffolding projects, and managing DB tables.
- `bot/core/` – Runtime wiring: `bot.py`, plugin loader, event bus, prefix message handler, and Discord permission utilities.
- `bot/plugins/` – Framework primitives (`BasePlugin`, command registry, argument parsing, decorators).
- `bot/web/` – FastAPI web control panel: `WebApp` hosts routes/templates, `WebPanelManager` manages plugin panels, `DiscordAuth` handles OAuth, and `redis_session.py` adds optional Redis-backed sessions.
- `bot/database/` – Async SQLAlchemy manager plus ORM models for guilds, users, permission grants, command analytics, and the music queue/session tables.
- `bot/permissions/` – Role-based permission manager and decorators (`requires_permission`, `requires_role`, `requires_guild_owner`, `requires_bot_permissions`).
- `bot/middleware/` – Optional event middleware for logging, analytics, and error collection (attach via `EventSystem.add_middleware`).
- `plugins/` – First-party plugin packages (`admin`, `fun`, `help`, `moderation`, `utility`, `music`) plus authoring guide in `plugins/README.md`.
- `config/settings.py` – Pydantic settings model; exposes a singleton `settings` used across the app. Environment variables live in `.env`.
- `tests/` – Pytest suite organised by domain (`tests/unit/bot/...` for framework, `tests/unit/plugins/<name>/...` for plugin coverage). Fixtures reside in `tests/conftest.py`.

## 3. Runtime building blocks
- **DiscordBot (`bot/core/bot.py`)**: Handles lifecycle events, subscribes to gateway events, initializes subsystems, forwards guild messages to the prefix handler, and exposes helpers such as `add_startup_task` and `get_guild_prefix`.
- **Plugin loader (`bot/core/plugin_loader.py`)**: Discovers packages from `settings.plugin_directories`, reads `PLUGIN_METADATA`, instantiates subclasses of `bot.plugins.base.BasePlugin` (or a `setup` factory), applies dependency checks, and manages plugin load/unload lifecycles.
- **Event system (`bot/core/event_system.py`)**: Publish/subscribe bus with async middleware hooks. Use `@event_listener("event_name")` within plugins to auto-register handlers, and `bot.event_system.add_middleware(...)` for cross-cutting concerns.
- **Prefix commands (`bot/core/message_handler.py`)**: `MessageCommandHandler` inspects messages starting with `settings.bot_prefix`, creates a `PrefixContext`, enforces permission nodes when provided, and delegates argument parsing to `bot.plugins.commands.ArgumentParserFactory`.
- **Permissions (`bot/permissions/manager.py`)**: `PermissionManager` caches granted nodes per guild role, seeds defaults (admin/moderation/utility/fun/music), applies hierarchy rules (e.g., `admin.*` grants everything), and backs the Lightbulb decorators in `bot/permissions/decorators.py`.
- **Database (`bot/database/manager.py` & `bot/database/models.py`)**: Async engine selection for SQLite or PostgreSQL. Always interact via `async with db_manager.session():` and commit inside the context. Models cover guild configuration, users, role permissions, command usage, plugin settings, and music queues/sessions.
- **Web panel (`bot/web`)**: `WebPanelManager` orchestrates the FastAPI app, plugin panel registration, and background server task. `WebApp` wires templates, Redis session middleware, and Discord OAuth via `DiscordAuth`. Redis is optional—`RedisSessionStore` transparently falls back to in-memory sessions if `redis.asyncio` is unavailable.

## 4. Plugin authoring & extension
- Package layout: `plugins/<slug>/__init__.py` exports the plugin class (or `setup` factory) and declares `PLUGIN_METADATA`; the implementation module(s) subclass `BasePlugin`.
- `BasePlugin` features:
  - Lifecycle hooks `on_load` / `on_unload` automatically register/unregister slash and prefix commands discovered via the decorators in `bot.plugins.commands`.
  - Helpers: `create_embed`, `smart_respond` (handles ephemeral logic), `log_command_usage`, plus per-guild settings helpers (`get_setting`, `set_setting`, enable/disable toggles).
  - Automatically tracks event listeners flagged with `@event_listener` and registers them against the shared `EventSystem`.
- Command registration is handled by `CommandRegistry`: slash commands get dynamically generated Lightbulb classes (with option descriptors from `OptionDescriptorFactory`), while prefix commands use `MessageCommandHandler` with parsing performed by `ArgumentParserFactory`. Always express inputs with `CommandArgument` to stay compatible with both invocation styles.
- Unified command decorator (`bot/plugins/commands/decorators.py::command`): define `name`, `description`, optional aliases, `permission_node`, and a shared `arguments` list of `CommandArgument`. Slash commands receive Lightbulb option descriptors; prefix commands are wrapped with `PrefixCommand` instances and parsed via `ArgumentParserFactory` (string, int, bool, user, channel, role, mentionable).
- Respect permission nodes: declare required nodes in `PLUGIN_METADATA["permissions"]`, guard handlers with `permission_node="plugin.node"` or manual decorator stacking, and update tests if access rules change.
- For plugins needing persistence, use the provided database models or introduce new ORM entities in `bot/database/models.py` (with accompanying migrations/tests). Leverage `BasePlugin.get_setting`/`set_setting` for lightweight per-guild configuration.
- Music plugin specifics live in `plugins/music/`; it integrates Lavalink (see `config.settings` for connection fields) and persists queue/session state. Install optional extras (`uv sync --extra music`) when modifying those components.
- Web-enabled plugins should inherit `WebPanelMixin` to expose control-panel pages. Implement `get_panel_info()` for navigation metadata, register FastAPI routes inside `register_web_routes()`, and use `render_plugin_template()` to load plugin-specific Jinja templates (which can extend `bot/web/templates/plugin_base.html`). Static assets can live in a `static/` directory; `WebPanelManager` will mount them automatically when provided.

## 5. Configuration & environment
- Settings are centrally provided by `config.settings.settings` (Pydantic). Modify defaults thoughtfully and document new fields in `README.md` or `.env.example`.
- Development vs production: the CLI `run --dev` flag sets `ENVIRONMENT=development`. Docker workflows are defined in `docker-compose.dev.yml` / `docker-compose.yml`.
- Secrets (`DISCORD_TOKEN`, etc.) should be referenced via environment variables; never hard-code tokens.
- Web/OAuth configuration uses `web_host`, `web_port`, `web_secret_key`, and Discord OAuth credentials (`discord_client_id`, `discord_client_secret`, `discord_redirect_uri`). Redis-backed sessions rely on `redis_url`, `redis_session_prefix`, and `redis_session_ttl` but gracefully degrade if Redis is unavailable. Music playback depends on Lavalink (`lavalink_*`) and optional Spotify tokens—keep `.env` in sync when adjusting these.

## 6. Coding standards & tooling
- Target **Python 3.11+** with comprehensive type hints. Maintain async/await boundaries—avoid blocking IO in event handlers or commands.
- Formatting: Black with **135 character** max line length (`pyproject.toml`). Run `uv run black .` when needed.
- Linting: Ruff enforces error codes `E,F,W,I,N,UP,S,B,A,C4,T20`. Execute `uv run ruff check .` (tests are excluded by default).
- Logging: use `logging.getLogger(__name__)`; avoid `print`. Follow existing message styles (info for lifecycle, debug for verbose traces, warning/error for failures).
- Discord interactions: prefer rich embeds via `BasePlugin.create_embed` and respond through `BasePlugin.smart_respond` to unify slash/prefix behaviour.
- Permission/DB helpers already handle caching and error logging; prefer extending them over duplicating logic.
- FastAPI templates reside in `bot/web/templates/`; extend `base.html`/`plugin_base.html` for new pages and keep Tailwind-compatible class naming. Avoid blocking calls inside web handlers—stick to async I/O.

## 7. Testing expectations
- Unit tests live under `tests/unit/bot/` (core) and `tests/unit/plugins/<plugin>/`. Mirror new behaviour with corresponding tests.
- Default coverage threshold is **70%** (`run_tests.py`, `pyproject.toml`). Running `uv run pytest` (or `make test`) with coverage is the baseline; add `--cov` flags for focused runs (`uv run pytest tests/unit/plugins/admin --cov=plugins/admin`).
- `python run_tests.py --separate-coverage` executes suites per plugin and generates HTML reports in `htmlcov/`.
- Async tests rely on `pytest-asyncio` (`asyncio_mode = auto`). Use provided fixtures in `tests/conftest.py` to stub Discord objects, database sessions, and plugin instances.
- When altering CLI/database tooling, add regression coverage under `tests/unit/bot/test_cli.py` or similar.
- Web-surface changes (FastAPI routes, templates, Redis session logic) should be exercised via the existing unit tests or supplemented with new ones under `tests/unit/web/` (create if missing) to keep coverage meaningful.

## 8. Helpful commands
- `python -m bot` – start the gateway bot (use `--dev` for development mode).
- `python -m bot.cli` – inspect CLI commands (`run`, `plugins`, `db`, `init`).
- `make help` – discover Make targets (`make lint`, `make format`, `make test`, `make install-dev`, etc.).
- `uv run pytest` – primary test command; `uv sync --extra dev` installs dev dependencies.
- `make db-create` / `make db-reset` – manage schema during development (uses async SQLAlchemy).
- `python run_tests.py --separate-coverage` – run coverage-partitioned test suites for the core and each plugin.
- `make bot-dev` – launch the bot (and FastAPI panel) via Docker Compose for local experimentation.

## 9. Collaboration tips
- Keep plugins decoupled: communicate via the `EventSystem` or shared database tables instead of direct cross-plugin imports when possible.
- Clean up external resources (aiohttp sessions, background tasks) inside `on_unload` to avoid resource leaks and ensure stable unloads.
- Update documentation (`README.md`, plugin-specific READMEs) whenever commands, permissions, or environment variables change.
- If new conventions emerge for a subdirectory, add a nested `AGENTS.md` with scoped instructions so future agents inherit the context.
- Coordinate web-panel adjustments with plugin authors: ensure new routes respect `DiscordAuth` guard rails and navigation metadata, and tidy up Redis session keys on unload when storing long-lived state.
