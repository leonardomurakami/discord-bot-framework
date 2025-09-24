# Fun Plugin Guidelines

## Overview
- Delivers entertainment commands (jokes, memes, quotes, facts) and lightweight games (dice rolls, coin flips).
- Provides interactive Miru views for would-you-rather prompts with button-based responses.
- Maintains an `aiohttp.ClientSession` for calling external APIs with graceful fallbacks to bundled defaults.
- Primary permission nodes:
  - `basic.fun.games.play` – shared by all game-oriented commands.
  - `basic.fun.images.view` – protects meme/image retrieval commands.
- Optional web panel (`/plugin/fun`) can surface high scores or activity metrics via FastAPI routes.

## Architecture
- `plugin.py` defines `FunPlugin` which inherits `BasePlugin` and `WebPanelMixin`. It initialises an `aiohttp` session in `on_load`
  and closes it during `on_unload`.
- `commands/`
  - `basic.py` – contains `/ping` health check.
  - `games.py` – RNG utilities (`/roll`, `/coinflip`, `/8ball`, `/choose`, `/random`) and would-you-rather (`/would-you-rather`). All routes use `basic.fun.games.play`.
  - `content.py` – content fetchers (`/joke`, `/quote`, `/meme`, `/fact`). Only `/meme` requires `basic.fun.images.view`; others are
    public.
- `config.py` supplies API endpoints, default fallback data, RNG limits, and emoji sets for embed decoration.
- `views/` exposes `WouldYouRatherView` used by the interactive commands.
- `web/` (optional) can register panel routes via `register_fun_routes`; currently a placeholder for future expansion.
- The plugin does not persist state beyond runtime counters (no custom models). Shared logging happens through `plugin.log_command_usage`.

## Commands
| Command | Description | Permission Node |
| --- | --- | --- |
| `/ping` | Quick responsiveness check. | _None_ |
| `/roll [dice]` | Roll dice using NdN notation; validates ranges defined in `config.DICE_LIMITS`. | `basic.fun.games.play` |
| `/coinflip` | Flip a coin with emoji-rich output. | `basic.fun.games.play` |
| `/8ball <question>` | Magic 8-ball style responses. | `basic.fun.games.play` |
| `/choose <option1> <option2>` | Choose between supplied options. | `basic.fun.games.play` |
| `/random [min] [max]` | Random integer within configurable bounds. | `basic.fun.games.play` |
| `/would-you-rather` | Presents a prompt with button reactions for A/B choices. | `basic.fun.games.play` |
| `/joke` | Fetches a random joke via API or fallback list. | _None_ |
| `/quote` | Provides motivational quotes with attribution. | _None_ |
| `/meme` | Pulls memes from configured APIs, falls back to Imgflip if necessary. | `basic.fun.images.view` |
| `/fact` | Returns a random educational fact. | _None_ |

## Configuration
- All external endpoints live in `config.API_ENDPOINTS`; adjust or extend this mapping when adding new content sources.
- RNG and game defaults are also defined in `config.py`:
  - `DICE_LIMITS` and `RANDOM_NUMBER_LIMIT` bound numeric outputs.
  - `DEFAULT_WYR_QUESTIONS` and other fallback lists keep commands functional offline.
- No plugin-specific environment variables; relies on the global `config.settings` for tokens and bot metadata.
- HTTP interactions require the `aiohttp` extra declared in the project dependencies.

## Development Guidelines
- Always guard API calls with `if plugin.session:` and provide fallback data; the existing commands model this pattern.
- Register new commands through the factory functions in `commands/` and let `_register_commands()` attach them.
- Prefer `plugin.smart_respond` for outputs so slash/prefix parity is preserved.
- Reuse logging helpers (`plugin.log_command_usage`) to capture metrics in the shared database.
- Update `config.py` when adding new emojis, endpoints, or range constants so future contributors have a single source of truth.
- Run plugin tests after changes: `uv run pytest tests/unit/plugins/fun`.

## Troubleshooting
- **HTTP failures**: All commands already fall back to bundled defaults. If you see repeated errors in logs, verify outbound
  connectivity and inspect the JSON structure of upstream APIs.
- **Miru interactions not responding**: ensure the global Miru client is initialised. Interactive views log debugging information when
  failing to start.
- **Rate limiting**: APIs used (`Official Joke API`, `Quotable`, `wttr.in`) are public but may throttle; consider caching responses
  or adding more fallback data.

## Examples
### Adding a new content command
```python
from bot.plugins.commands import command

@command(name="fact-cat", description="Cat-themed facts")
async def cat_fact(ctx: lightbulb.Context) -> None:
    if not plugin.session:
        fact = "Cats sleep for 70% of their lives."
    else:
        async with plugin.session.get("https://catfact.ninja/fact") as resp:
            data = await resp.json()
            fact = data.get("fact", "Cats have flexible spines for quick jumps.")
    embed = plugin.create_embed(title="🐱 Cat Fact", description=fact)
    await ctx.respond(embed=embed)
```


Follow these conventions to ensure new commands integrate smoothly with the existing session handling and UI patterns.
