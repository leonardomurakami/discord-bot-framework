# Music Plugin Guidelines

## Overview
- Feature-rich music system backed by [Lavalink](https://github.com/freyacodes/Lavalink). Supports queue persistence, playback
  controls, search, history, and per-guild settings.
- Persists queues and session metadata in the shared database so playback can resume after restarts.
- Exposes a FastAPI web panel (`/plugin/music`) for queue inspection and management in the browser.
- Primary permission nodes:
  - `music.manage` – grants full management (queue/voice/settings) to a role.
  - `basic.music.playback.control`
  - `basic.music.queue.view`
  - `basic.music.queue.control`
  - `basic.music.voice.control`
  - `basic.music.search.use`
  - `music.queue.manage`
  - `music.voice.manage`
  - `music.settings.manage`

## Architecture
- `plugin.py` defines `MusicPlugin` (inherits `DatabaseMixin`, `BasePlugin`, and `WebPanelMixin`). Responsibilities include:
  - Registering command factories from `commands/`.
  - Initialising the Lavalink client using host/port/password settings from `config.settings`.
  - Listening to Hikari voice events and forwarding them to Lavalink.
  - Restoring persisted queues on startup via `restore_all_queues`.
- `commands/`
  - `playback.py` – playback lifecycle (`/play`, `/pause`, `/resume`, `/stop`, `/skip`, `/seek`, `/position`). Uses
    `basic.music.playback.control`.
  - `queue.py` – queue viewing, shuffle, loop, and management commands. View/control actions use `basic.music.queue.view` /
    `basic.music.queue.control`; destructive operations use `music.queue.manage`.
  - `voice.py` – join/disconnect/volume commands. `basic.music.voice.control` for join/volume, `music.voice.manage` for disconnects.
  - `search.py` – interactive search with dropdown selection. Requires `basic.music.search.use`.
  - `nowplaying.py` & `history.py` – informational embeds for current track and history using `basic.music.queue.view`.
  - `settings.py` – guild-specific settings such as auto-disconnect timer (`music.settings.manage`).
- `models/__init__.py` defines `MusicQueue` and `MusicSession` for persistence.
- `events.py` attaches Lavalink event hooks and handles auto-disconnect/queue saving logic.
- `utils.py` centralises queue persistence, repeat mode handling, and auto-disconnect timers.
- `web/` supplies FastAPI routes and WebSocket helpers for the control panel. Templates live in `templates/` (Jinja2).

## Commands (Highlights)
| Command | Description | Permission Node |
| --- | --- | --- |
| `/play <query>` | Add a track/playlist to the queue and start playback. | `basic.music.playback.control` |
| `/pause`, `/resume`, `/stop`, `/skip`, `/seek`, `/position` | Control playback state. | `basic.music.playback.control` |
| `/queue [page]` | View current queue with pagination. | `basic.music.queue.view` |
| `/shuffle`, `/loop [mode]` | Non-destructive queue controls. | `basic.music.queue.control` |
| `/remove <position>`, `/move <from> <to>`, `/clear` | Modify or clear the queue. | `music.queue.manage` |
| `/join`, `/volume [level]` | Voice channel join and volume adjustments. | `basic.music.voice.control` |
| `/disconnect` | Disconnect the bot and clear queue. | `music.voice.manage` |
| `/search <query>` | Interactive search with dropdown results. | `basic.music.search.use` |
| `/nowplaying`, `/history [page]` | Display currently playing track and history. | `basic.music.queue.view` |
| `/music-settings [setting] [value]` | Configure per-guild options like auto-disconnect timer. | `music.settings.manage` |

## Configuration
- Required settings: `lavalink_host`, `lavalink_port`, `lavalink_password` (set in `.env`/`config.settings`).
- Optional extras: Spotify credentials (if using the Lavalink Spotify plugin) should be configured globally.
- The auto-disconnect timer is stored per guild via `BasePlugin.get_setting`/`set_setting` under the key `"auto_disconnect_timer"`.
- Queue persistence writes to the shared database through `MusicQueue`/`MusicSession` models. Ensure migrations run before enabling
  the plugin.

## Development Guidelines
- Always obtain the Lavalink player via `self.lavalink_client.player_manager.get(guild_id)` to reuse existing connections.
- Guard against DM usage – most commands exit early if `ctx.guild_id` is `None`.
- After editing queue structures call `save_queue_to_db` and broadcast updates using `broadcast_music_update` so the web panel stays
  in sync.
- Use `plugin.repeat_modes` for tracking per-guild repeat status (0=off, 1=track, 2=queue).
- Register new command factories in `_register_commands()` to ensure they are attached on load.
- When adding new settings, update `settings.py` and persist through the plugin setting helpers.
- Run targeted tests: `uv run pytest tests/unit/plugins/music` (add coverage as features expand).

## Troubleshooting
- **Lavalink connection fails**: verify host/port/password match the Lavalink server configuration. The plugin logs connection
  errors to aid diagnosis.
- **Bot stays connected to empty voice channels**: check the auto-disconnect timer (`/music-settings auto_disconnect_timer <minutes>`)
  and ensure `check_voice_channel_empty` is invoked (voice events must reach the bot).
- **Queue not persisting**: confirm the music tables exist (`MusicQueue`, `MusicSession`) and database writes succeed. Inspect logs for
  SQL errors.
- **Search dropdown missing**: Miru must be installed and initialised. If Miru is absent the command falls back to auto-adding the
  first search result.

## Examples
### Adjusting the auto-disconnect timer programmatically
```python
await plugin.set_setting(ctx.guild_id, "auto_disconnect_timer", 10)  # minutes
```

### Granting queue management rights to DJs
```python
# /permission grant @DJs music.queue.manage
```

Follow these guidelines to keep new music features robust, performant, and in sync with the rest of the framework.
