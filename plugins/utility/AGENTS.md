# Utility Plugin Guidelines

## Overview
- Collection of practical utilities: user/server info, weather, QR codes, reminders, polls, timestamp conversions, color analysis,
  and text transformations.
- Maintains an `aiohttp.ClientSession` for external HTTP requests (weather, “On This Day” data) with graceful degradation.
- Primary permission nodes:
  - `basic.utility.info.view`
  - `basic.utility.convert.use`
  - `basic.utility.tools.use`

## Architecture
- `plugin.py` defines `UtilityPlugin`, creates the shared HTTP session in `on_load`, and registers command factories.
- `commands/`
  - `info.py` – guild/user info, avatar retrieval, weather lookup. Uses `basic.utility.info.view`.
  - `convert.py` – timestamp formatting, base64 encode/decode, color info, hashing, translation helpers. Uses a mix of
    `basic.utility.convert.use` and `basic.utility.tools.use` depending on functionality.
  - `tools.py` – reminders, polls, QR code generation, “On This Day” history, countdown timers. Uses `basic.utility.tools.use`.
- `config.py` centralises constants (API endpoints, colours, limits) for commands to import.
- `utils.py` exposes helper functions (e.g., `parse_timestamp_input`, `rgb_to_hsl`).
- Web/template directories are placeholders for future web panel functionality.

## Commands (Highlights)
| Command | Description | Permission Node |
| --- | --- | --- |
| `/userinfo [user]` | Rich user profile embed including roles and key permissions. | `basic.utility.info.view` |
| `/avatar [user]` | High resolution avatar viewer. | `basic.utility.info.view` |
| `/weather <location>` | Weather summary using wttr.in API. | `basic.utility.info.view` |
| `/timestamp [input]` | Converts time into Discord timestamp formats. | `basic.utility.convert.use` |
| `/base64 <encode|decode> <text>` | Base64 conversion helper. | `basic.utility.convert.use` |
| `/color <value>` | Displays color information from hex/name. | `basic.utility.tools.use` |
| `/qr <text>` | Generates a QR code using quickchart.io. | `basic.utility.tools.use` |
| `/remind <time> <message>` | Creates a reminder with background task scheduling. | `basic.utility.tools.use` |
| `/poll <question> [options...]` | Quick reaction poll creation. | `basic.utility.tools.use` |
| `/onthisday <date|relative>` | Historical facts for the supplied date. | `basic.utility.tools.use` |

## Configuration
- `config.py` contains numerous constants:
  - API endpoints (`API_ENDPOINTS`) for jokes, memes, weather, QR codes, etc.
  - Embed colours (`INFO_COLOR`, `ERROR_COLOR`, `POLL_COLOR`, etc.).
  - Limits (e.g., `QR_TEXT_LIMIT`, `REMINDER_MAX_DURATION`).
- No environment variables; relies on the global bot settings for tokens and HTTP proxies if needed.
- Commands gracefully degrade when `plugin.session` is `None` by using fallback data or aborting with helpful errors.

## Development Guidelines
- Use the shared `plugin.session` for outbound HTTP calls and guard with `if not plugin.session: ...` as existing commands do.
- Wrap long-running background tasks (e.g., reminders) with appropriate cleanup to avoid leaving stray tasks on unload.
- Share embed styling via `plugin.create_embed` and reuse colour constants from `config.py`.
- Validate all user input (time formats, URLs, number ranges). Many helper functions already exist in `utils.py` and `config.py`.
- Register new commands through the factory modules and update tests in `tests/unit/plugins/utility`.

## Troubleshooting
- **HTTP dependent commands failing**: check network connectivity and API availability. Many commands already catch exceptions and
  fall back to built-in datasets.
- **Reminders not firing**: ensure the bot process remains running; reminders rely on in-memory tasks, not persistent jobs.
- **Color or timestamp parsing errors**: review `utils.py` helpers and update validation to cover new formats.

## Examples
### Adding a custom conversion command
```python
@command(name="slugify", description="Convert text to URL-friendly slug", permission_node="basic.utility.convert.use")
async def slugify(ctx: lightbulb.Context, text: str) -> None:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    await ctx.respond(f"`{slug}`")
```

### Scheduling a reminder from another plugin
```python
await plugin.bot.reminder_manager.schedule(ctx.guild_id, ctx.author.id, "Check the raid", delay=3600)
```

Keep new utilities consistent with these patterns to maintain reliability across the toolset.
