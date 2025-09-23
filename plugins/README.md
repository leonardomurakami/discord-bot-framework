# Plugin Development Guide

This document explains how to build, structure, and maintain plugins for the Discord bot framework. It covers:

- Bootstrapping a new plugin package
- Defining the metadata that the loader consumes
- Understanding the services exposed through `BasePlugin`
- Common patterns for commands, events, database access, and permissions

If you are extending existing plugins, pair this guide with any local `AGENTS.md` instructions that live beside the plugin.

## Quick start

### 1. Create a package

Each plugin lives inside `plugins/<slug>/`. A minimal layout looks like this:

```
plugins/
├── my_plugin/
│   ├── __init__.py          # exports and metadata (required)
│   └── plugin.py            # plugin implementation (convention)
└── README.md
```

### 2. Define metadata and exports

`__init__.py` must expose your plugin subclass (or a `setup()` factory) and the accompanying `PLUGIN_METADATA` dictionary. Example:

```python
from .plugin import MyPlugin

PLUGIN_METADATA = {
    'name': 'My Plugin',
    'version': '1.0.0',
    'author': 'Your Name',
    'description': 'Short description of what the plugin does',
    'permissions': ['my_plugin.use', 'my_plugin.admin'],
    'dependencies': ['admin'],  # optional list of plugin slugs you require
}

__all__ = ['MyPlugin']
```

If you prefer a factory-style export, implement a `setup(bot)` function that returns the plugin instance.

### 3. Implement the plugin class

Subclass `bot.plugins.base.BasePlugin` and register commands using the shared decorators.

```python
import hikari
from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command


class MyPlugin(BasePlugin):
    @command(
        name='greet',
        description='Send a greeting',
        permission_node='my_plugin.use',
        arguments=[CommandArgument('user', hikari.OptionType.USER, 'Who to greet')],
    )
    async def greet(self, ctx, user: hikari.User) -> None:
        async with self.track_command(ctx, 'greet'):
            await self.respond_success(
                ctx,
                f'Hello {user.mention}! 👋',
                command_name='greet',
                ephemeral=False,
            )
```

Once the package exists and is listed in `config/settings.py::settings.enabled_plugins`, the loader will discover it automatically.

## Plugin metadata reference

`PluginLoader` consumes `PLUGIN_METADATA` to display and enforce information about each plugin. Supported keys:

| Field          | Required | Description |
| -------------- | -------- | ----------- |
| `name`         | ✅       | Display name shown in UIs and logs. |
| `version`      | ✅       | Semantic version string. |
| `author`       | ✅       | Author or maintainer attribution. |
| `description`  | ✅       | Short summary of the plugin. |
| `permissions`  | ⚠️       | List of permission nodes this plugin may enforce. Optional but recommended so defaults can be seeded. |
| `dependencies` | ⚠️       | List of plugin slugs that must load before this one. |

Additional keys are passed through unchanged, so you may add custom metadata for your own tooling. Keep names snake_case.

## BasePlugin lifecycle and services

`BasePlugin` wires your plugin into the framework. It automatically registers decorated commands and event listeners during `on_load()` and reverses the process in `on_unload()`.

Every plugin instance receives cached references to the most common services. Use these instead of reaching back through `self.bot`:

| Attribute        | Type or source            | Purpose |
| ---------------- | ------------------------- | ------- |
| `self.logger`    | `logging.Logger`          | Plugin scoped logger named `plugin.<slug>`. |
| `self.db`        | `DatabaseManager`         | Async SQLAlchemy session factory and model registry. |
| `self.events`    | `EventSystem`             | Publish or listen for framework level events. |
| `self.permissions` | `PermissionManager`     | Query and mutate permission grants. |
| `self.web_panel` | `WebPanelManager` or `None` | Register FastAPI routes when using `WebPanelMixin`. |
| `self.command_client` | `lightbulb.LightbulbApp` | Slash command registration and introspection. |
| `self.gateway`   | `hikari.GatewayBot`       | Access REST, cache, and voice helpers via `self.rest` and `self.cache`. |
| `self.rest`      | `hikari.api.RESTClient`   | Perform REST calls such as `fetch_user`. |
| `self.cache`     | `hikari.api.CacheView`    | Inspect cached guild, member, and voice state objects. |
| `self.services`  | `dict[str, Any]`          | Snapshot of the bot wide service registry. |

For advanced scenarios reach the full bot via `self.bot`, or resolve additional services with `self.bot.get_service('name')`.

### Helper methods

`BasePlugin` exposes utilities that eliminate boilerplate:

- **Responding**: `create_embed()`, `smart_respond()`, `respond_success()`, and `respond_error()` standardise messaging and analytics.
- **Command analytics**: `track_command()` and `log_command_usage()` capture success or failure automatically.
- **Database access**: `db_session()` async context manager and `with_session(callback)` helper wrap the shared SQLAlchemy session.
- **Settings**: `get_setting()`, `set_setting()`, `is_enabled_in_guild()`, `enable_in_guild()`, `disable_in_guild()` provide per guild configuration storage.
- **Events**: `emit_event(name, *args, suppress_errors=True)` proxies to the event bus with optional error suppression.
- **Discord clients**: `fetch_user()`, `fetch_channel()`, `update_voice_state()`, and `get_voice_state()` utilise the shared gateway and REST clients.
- **Miscellaneous**: `get_guild_prefix(guild_id)` returns the effective prefix using the bot helper.

Refer to `bot/plugins/base.py` for the full catalogue.

## Commands

Commands are registered through `bot.plugins.commands.decorators.command`. The decorator abstracts both slash and prefix command creation and accepts shared argument descriptors.

```python
from bot.plugins.commands import CommandArgument, command
import hikari

@command(
    name='purge',
    description='Delete the last N messages',
    permission_node='my_plugin.moderate',
    arguments=[
        CommandArgument('amount', hikari.OptionType.INTEGER, 'How many messages', min_value=1, max_value=100),
    ],
)
async def purge(self, ctx, amount: int) -> None:
    async with self.track_command(ctx, 'purge'):
        deleted = await self._purge_messages(ctx.channel_id, amount)
        await self.respond_success(ctx, f'Deleted {deleted} messages', command_name='purge')
```

Inside the handler you interact with the Lightbulb context `ctx`. `respond_success()` and `respond_error()` handle ephemeral flags correctly for slash invocations while still working for prefix commands.

## Event handling

Two approaches are available:

1. **Framework events** – Use the event bus for cross plugin communication.

    ```python
    from bot.core.event_system import event_listener

    class MyPlugin(BasePlugin):
        @event_listener('bot_ready')
        async def announce_ready(self, bot) -> None:
            self.logger.info('Bot is ready; loaded plugins: %s', len(bot.plugin_loader.get_loaded_plugins()))
    ```

    Decorated methods are auto registered during `on_load()` and cleaned up during `on_unload()`.

2. **Gateway events** – Listen directly to Hikari events when you need raw Discord payloads.

    ```python
    class MyPlugin(BasePlugin):
        async def on_load(self) -> None:
            await super().on_load()

            @self.gateway.listen(hikari.GuildMessageCreateEvent)
            async def handle_message(event: hikari.GuildMessageCreateEvent) -> None:
                if event.is_bot or not event.content:
                    return
                await self.emit_event('message_logged', event)
    ```

    Remember to unregister manual listeners in `on_unload()` if you add any yourself.

## Database access

Use the shared manager instead of creating your own engines:

```python
from datetime import UTC, datetime
from sqlalchemy import select
from bot.plugins.mixins import DatabaseMixin
from .models import Reminder

class RemindersPlugin(DatabaseMixin, BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.register_model(Reminder)

    async def fetch_due(self) -> list[Reminder]:
        async with self.db_session() as session:
            result = await session.execute(select(Reminder).where(Reminder.due_at <= datetime.now(UTC)))
            return result.scalars().all()
```

- `DatabaseMixin` (see `bot/plugins/mixins.py`) registers models so tables are created at startup.
- `db_session()` guarantees commits or rollbacks and reuses the shared engine.

## Permissions

Declare required nodes in `PLUGIN_METADATA['permissions']`. Commands can opt in to enforcement via `permission_node`.

```python
@command(
    name='reload',
    description='Reload this plugin',
    permission_node='my_plugin.admin',
)
async def reload_self(self, ctx) -> None:
    await self.bot.plugin_loader.reload_plugin(self.name)
    await self.respond_success(ctx, 'Plugin reloaded', command_name='reload')
```

Use the permission manager directly for advanced logic:

```python
if await self.permissions.has_permission(ctx.guild_id, ctx.author.id, 'my_plugin.special'):
    ...
```

## Web panel integration

Plugins that expose web routes should inherit `bot.web.mixins.WebPanelMixin`. Implement `register_web_routes()` and optionally `get_panel_info()`. During `on_load()` the mixin hooks into `WebPanelManager` so your FastAPI routes become part of the control panel automatically.

## Best practices

- Prefer the helpers in `BasePlugin` instead of touching `self.bot.hikari_bot` or `self.bot.db` directly.
- Wrap potentially failing command bodies in `track_command()` to capture success and failure metrics automatically.
- Emit custom events rather than calling into other plugins to keep integrations loosely coupled.
- Keep metadata and permission nodes in sync with actual command behaviour.
- Update or add tests under `tests/unit/plugins/<slug>/` when introducing new behaviour.

With these building blocks you can create powerful, well integrated plugins that feel consistent across the framework.
