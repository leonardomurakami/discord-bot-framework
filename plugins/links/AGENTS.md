# Links Plugin Guidelines

## Overview
- Stores curated links (documentation, support, custom resources) per guild with rich embed presentations.
- Ships a set of default global links (GitHub, docs, panel, support) exposed through `DefaultLinkCommands`.
- Supports full CRUD for guild-specific links with permission-guarded commands.
- Primary permission nodes:
  - `basic.links.view` – allows everyone to browse default/custom links.
  - `links.collection.manage` – required to create, edit, or delete stored links.
  - `links.manage` – optional aggregator granting full CRUD access to the plugin.

## Architecture
- `plugin.py` defines `LinksPlugin`, inheriting `DatabaseMixin` and `BasePlugin`.
  - Registers the `Link` SQLAlchemy model and initialises command handler classes (`LinkCommands`, `DefaultLinkCommands`).
- `commands/`
  - `default_link_commands.py` – static showcase commands for core project links. Each command uses `basic.links.view` and renders
    informative embeds.
  - `link_commands.py` – user-managed link operations (`/links`, `/link add`, `/link remove`, `/link edit`, `/link info`). Management
    routes require `links.collection.manage`.
- `models/__init__.py` – contains the `Link` ORM model with guild/name uniqueness enforcement and relationships to `Guild`/`User`.
- `config.py` exposes `links_settings` (default links and embed colours) to keep configuration centralised.
- No templates or web routes are defined yet, but directories are present for future panel expansion.

## Commands
| Command | Description | Permission Node |
| --- | --- | --- |
| `/github`, `/panel`, `/docs`, `/support` | Static links populated from `links_settings.default_links`. | `basic.links.view` |
| `/links` | Lists guild-specific links with pagination. | `basic.links.view` |
| `/link info <name>` | Displays a single stored link. | `basic.links.view` |
| `/link add <name> <url> [description]` | Creates a new link entry. | `links.collection.manage` |
| `/link edit <name> [url] [description]` | Updates existing link metadata. | `links.collection.manage` |
| `/link remove <name>` | Deletes a stored link. | `links.collection.manage` |

## Configuration
- Default links live in `config.py` under `links_settings.default_links`; update this mapping to adjust the stock commands.
- The ORM model ensures `(guild_id, name)` uniqueness. Names are capped at 50 characters via the schema to avoid embed overflow.
- No environment variables are required. The plugin uses the shared database connection configured globally by the framework.

## Development Guidelines
- When adding new management commands, use the helper classes (`LinkCommands`, `DefaultLinkCommands`) to keep separation between
  system-provided and guild-provided links.
- Always validate user input (URL format, duplicate detection) before writing to the database; existing methods provide examples
  and throw descriptive errors.
- Wrap database operations in `async with plugin.bot.db.session():` contexts to ensure proper transaction handling.
- Reuse `plugin.create_embed` and `plugin.smart_respond` for consistent embed styling and ephemeral responses.
- Run plugin-specific tests after changes: `uv run pytest tests/unit/plugins/links` (create new tests if functionality expands).

## Troubleshooting
- **Link not saving**: check logs for unique constraint violations. Names must be unique per guild.
- **Embeds missing fields**: ensure descriptions stay within Discord embed limits (the commands truncate where necessary but
  additional custom logic should follow suit).
- **Permission errors**: verify the invoking role has `links.collection.manage` when performing mutations.

## Examples
### Adding a custom default link command
```python
class DefaultLinkCommands:
    # ... existing commands ...

    @command(name="status", description="Show the status page", permission_node="basic.links.view")
    async def status_link(self, ctx) -> None:
        embed = self.plugin.create_embed(
            title="📈 Service Status",
            description="Check real-time uptime information",
        )
        embed.add_field("Status Page", self.plugin._default_links["status"], inline=False)
        await self.plugin.smart_respond(ctx, embed=embed)
```

### Granting management access via admin command
```python
# /permission grant <role> links.manage
```

Keep new features consistent with these patterns to ensure links remain easy to manage and present.
