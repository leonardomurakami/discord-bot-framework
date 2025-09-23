# Help Plugin Guidelines

## Overview
- Centralised help system that mirrors both slash and prefix commands, complete with pagination and plugin filtering.
- Generates embeds dynamically using the command registry metadata and exposes a `/help` command with intelligent search.
- Integrates with Miru to render dropdown selection menus for plugin navigation and pagination controls.
- Primary permission nodes:
  - `basic.help.commands.view` – grants access to the `/commands` listing.
  - `basic.help.plugins.view` – allows viewing `/plugins` overview.
- Designed to work even when optional components (Miru, prefix handler) are unavailable by gracefully degrading to plain embeds.

## Architecture
- `plugin.py` exposes `HelpPlugin`, extending `BasePlugin`. It registers commands directly on the class rather than returning them
  from factories (help commands benefit from tight integration with the plugin state).
- `models/command_info.py` contains `CommandInfoManager`, responsible for caching command metadata gathered from the registry and
  the plugin loader.
- `views/`:
  - `embed_generators.py` holds reusable embed builders for general help, command listings, and plugin information.
  - `menus.py` defines Miru dropdowns/pagination (`PluginSelectWithPaginationView`).
- `templates/` and `web/` are placeholders for future web panel expansion; currently unused.
- No custom persistence; everything is derived from the in-memory command registry and `PLUGIN_METADATA` of loaded plugins.

## Commands
| Command | Description | Permission Node |
| --- | --- | --- |
| `/help [query]` | Smart help entry point. With no arguments shows an overview; with input searches for commands or plugins. | _None_ |
| `/commands` (`/cmds`) | Lists all registered commands grouped by plugin. | `basic.help.commands.view` |
| `/plugins` (`/plugin-list`) | Shows metadata (version, author, description, permissions) for loaded plugins. | `basic.help.plugins.view` |

## Configuration
- No environment variables or plugin-specific settings; the plugin introspects loaded plugins and command metadata at runtime.
- Behaviour toggles:
  - `config.py` exposes `HelpConfig` (see `show_permissions` flag) allowing consumers to configure whether permission nodes appear
    in the generated embeds.
- The plugin respects whichever command prefix is configured globally via `DiscordBot.get_guild_prefix` when building examples.

## Development Guidelines
- New helper methods should live in `views/embed_generators.py` to keep embed formatting centralised.
- When extending the help output, prefer editing `EmbedGenerators` rather than modifying command handlers directly.
- Miru components should be registered through `PluginSelectWithPaginationView`; ensure the global Miru client is started before
  expecting interactive elements to work.
- To expose additional metadata (e.g., usage analytics) extend `CommandInfoManager` to gather the necessary data.
- After modifying behaviour run `uv run pytest tests/unit/plugins/help` – the suite includes regression tests for embed content
  and permission visibility.

## Troubleshooting
- **Missing commands in help listings**: ensure new commands register metadata via the unified decorator (`bot.plugins.commands.command`).
- **Miru menus not showing**: double-check that Miru is installed and the bot initialises the global client. The help plugin will
  fall back to plain embeds if the view has no children.
- **Permission nodes absent from embeds**: confirm `HelpConfig.show_permissions` (in `config.py`) is `True`.

## Examples
### Extending the command listing
```python
from plugins.help.views.embed_generators import EmbedGenerators

class CustomEmbedGenerators(EmbedGenerators):
    async def get_commands_list(self) -> hikari.Embed:
        embed = await super().get_commands_list()
        embed.set_footer("Tip: Use /help <command> for detailed usage")
        return embed
```

### Registering a custom help page
```python
@command(name="staff-commands", description="List staff-specific utilities", permission_node="basic.help.commands.view")
async def staff_commands(self, ctx: lightbulb.Context) -> None:
    embed = self.create_embed(title="🛡️ Staff Utilities")
    embed.description = "\n".join("• `/mod action`" for action in ["ban", "timeout", "purge"])
    await ctx.respond(embed=embed)
```

Follow these conventions to keep the help system consistent and automatically discoverable.
