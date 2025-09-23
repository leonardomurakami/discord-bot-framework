# Discord Bot Framework

![Python](https://img.shields.io/badge/python-3.11+-blue.svg) ![Status](https://img.shields.io/badge/status-active-success.svg)

> A modern, plugin-driven Discord bot built on [Hikari](https://www.hikari-py.dev/), [Lightbulb](https://github.com/tandemdude/hikari-lightbulb), and [Lavalink](https://github.com/freyacodes/Lavalink), featuring async-first architecture, RBAC permissions, and an extensible web control panel.

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Installation Options](#installation-options)
- [Configuration](#configuration)
- [Plugin System](#plugin-system)
- [Permissions](#permissions)
- [Web Control Panel](#web-control-panel)
- [Testing & Quality](#testing--quality)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Documentation & Support](#documentation--support)

## Overview
The Discord Bot Framework is a batteries-included foundation for building scalable Discord bots. It couples a modular plugin
system with a robust permission model, asynchronous database manager, and optional FastAPI control panel. Core services (command
routing, event system, permissions, persistence, and analytics) live in `bot/`, while first-party functionality ships as
self-contained plugins under `plugins/`.

## Key Features
- 🔌 **Modular plugins** – enable/disable features per guild, ship custom plugins without touching the core.
- 🔐 **Hierarchical permissions** – role-based access control with wildcard support and web-based management.
- 🗃️ **Database persistence** – async SQLAlchemy models with SQLite (dev) or PostgreSQL (prod) backends.
- 🎛️ **Web panel** – optional FastAPI dashboard for managing plugins, permissions, and music queues.
- 🎵 **Full music stack** – Lavalink integration with queue persistence, auto-disconnect, and search selection UI.
- ⚙️ **CLI tooling** – Typer-based CLI for running the bot and managing the database.
- 🧪 **Comprehensive tests** – pytest suite organised by domain with async fixtures.

## Quick Start
### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Discord Bot Token
- Optional: running Lavalink server (required for the music plugin)

### Local Development Setup
```bash
# Clone the repository
git clone https://github.com/your-org/discord-bot-framework.git
cd discord-bot-framework

# Install dependencies (editable mode for development)
uv pip install -e .

# Copy environment template and populate secrets
cp .env.example .env
$EDITOR .env  # add DISCORD_TOKEN, database URL, Lavalink credentials, etc.

# Initialise the database schema
python -m bot.cli db create

# Launch the bot (development logging & settings)
python -m bot.cli run --dev
```

### Docker (Optional)
```bash
# Development stack (SQLite + hot reload)
docker compose -f docker-compose.dev.yml up

# Production profile (PostgreSQL + Lavalink)
docker compose --profile production up -d
```

## Installation Options
| Scenario | Suggested Command |
| --- | --- |
| Local development | `uv pip install -e .` |
| CI / deployment | `uv pip install .` or Docker image build |
| Install dev extras | `uv pip install -e .[dev]` |
| Install music extras | `uv pip install -e .[music]` (includes Lavalink client dependencies) |

## Configuration
1. **Environment variables** (`.env`)
   - `DISCORD_TOKEN` – required bot token.
   - `DATABASE_URL` – e.g. `sqlite+aiosqlite:///data/bot.db` (dev) or `postgresql+asyncpg://user:pass@host/db`.
   - `BOT_PREFIX` – prefix for message-based commands (default `!`).
   - `LAVALINK_HOST`, `LAVALINK_PORT`, `LAVALINK_PASSWORD` – required when the music plugin is enabled.
   - Web panel secrets (`WEB_SECRET_KEY`, `WEB_HOST`, `WEB_PORT`) if hosting the dashboard.

2. **Settings module** (`config/settings.py`)
   - Toggle enabled plugins via `settings.enabled_plugins`.
   - Configure plugin search paths and optional services (Redis sessions, analytics middleware, etc.).

3. **Permissions**
   - Default permission groups are seeded on first run. Use `/permission` (Admin plugin) or the admin web panel to manage
     role assignments.
   - See [docs/permissions/permission_audit.md](docs/permissions/permission_audit.md) for the canonical permission node list and
     [docs/permissions/migration.md](docs/permissions/migration.md) for migration guidance.

## Plugin System
Plugins live under `plugins/<name>/` and must expose a `PLUGIN_METADATA` dictionary plus a plugin class (usually in `plugin.py`).
Example metadata with the updated permission naming convention:

```python
# plugins/example/__init__.py
from .plugin import ExamplePlugin

PLUGIN_METADATA = {
    "name": "Example",
    "version": "1.0.0",
    "author": "Bot Framework",
    "description": "Demonstrates a custom feature",
    "permissions": [
        "basic.example.tools.use",
        "example.settings.manage",
    ],
}
```

Add optional aggregators (for example `"example.manage"`) when you want to grant a role the entire plugin surface with a single
assignment.

Command modules use the shared decorator from `bot.plugins.commands`:

```python
from bot.plugins.commands import command

@command(
    name="ping",
    description="Latency check",
    permission_node="basic.example.tools.use",
)
async def ping(ctx: lightbulb.Context) -> None:
    await ctx.respond("Pong!")
```

Each plugin ships an `AGENTS.md` guide tailored for LLM contributors (see `plugins/<name>/AGENTS.md`).

## Permissions
- Public commands should use the `basic.<plugin>.<feature>.<action>` prefix. Nodes starting with `basic.` are granted to everyone
  by default.
- Administrative commands use `<plugin>.<category>.<action>` (e.g. `music.queue.manage`, `admin.permissions.manage`).
- Plugin-wide aggregators such as `admin.manage`, `moderation.manage`, `music.manage`, and `links.manage` provide an easy way to
  grant a role every permission within a plugin without listing each node individually.
- Wildcards are supported: `admin.*`, `music.queue.*`, and `*.manage` map to matching concrete nodes. Aggregator nodes ending in
  `.manage` or `.admin` also cascade down their namespace.
- The permission hierarchy is enforced by `bot/permissions/manager.py`, which handles wildcards, aggregators, and the default
  `basic.` grants.

Refer to the [Permission Audit Report](docs/permissions/permission_audit.md) for a full legacy→modern mapping.

## Web Control Panel
- Located in `bot/web/`, powered by FastAPI with optional Redis-backed sessions.
- Plugins opt-in via `WebPanelMixin` and register routes under `/plugin/<name>`.
- Start the panel automatically with the bot (`python -m bot.cli run`) or run the FastAPI app directly if embedding elsewhere.
- Music plugin exposes real-time queue updates via WebSockets (`plugins/music/web/`).

## Testing & Quality
```bash
# Run all tests
uv run pytest

# Run plugin-specific tests
uv run pytest tests/unit/plugins/admin

# Linting (Ruff) & formatting (Black)
uv run ruff check .
uv run black --check .
```
Make targets (`make lint`, `make format`, `make test`) are also available for convenience.

## Troubleshooting
| Issue | Resolution |
| --- | --- |
| Bot starts but does nothing | Ensure `DISCORD_TOKEN` is valid and the bot has gateway intents enabled. |
| Music commands fail | Verify Lavalink server is running and credentials match `.env`. |
| Permissions not visible in panel | Run `/permission refresh` or restart the bot to trigger permission discovery. |
| Miru interactions do not respond | Confirm `miru` is installed and the bot initialises the global Miru client. |

## Contributing
1. Fork the repository and create a feature branch: `git checkout -b feature/my-change`.
2. Follow the repository coding standards (Black 135 char line length, Ruff lint rules).
3. Add or update tests covering your changes.
4. Run `uv run pytest` and lint/format commands before submitting.
5. Open a pull request describing the change and referencing relevant issues.

## Documentation & Support
- Plugin-specific implementation notes live in `plugins/<name>/AGENTS.md`.
- Permission reference and migration steps reside in `docs/permissions/`.
- The top-level [AGENTS.md](AGENTS.md) file outlines repository-wide expectations.
- For questions or feature requests, open a GitHub issue.
