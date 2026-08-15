# AI Plugin Guidelines

## Overview
- Lets Discord members chat with an AI model through the acpbox OpenAI-compatible endpoint.
- Exposes a unified `chat` command (`/chat` and `!chat`) accepting a free-text `message` argument.
- Maintains per-channel conversation memory (last N turns) in the `ai_conversation` table so users can hold ongoing threads.
- Provides a `clearai` command (`/clearai` and `!clearchat`) to reset a channel's history.
- Primary permission nodes:
  - `basic.ai.chat` – use the `chat` command (open to all by default).
  - `basic.ai.clear` – use the `clearai` command (open to all by default).

## Architecture
- `plugin.py` defines `AIPlugin(DatabaseMixin, BasePlugin)`. It registers the `AIConversation` model in `__init__`, creates an `aiohttp.ClientSession` in `on_load` (guarded by `ACPBOX_URL`/`AI_MODEL` presence — soft-fails with a warning if unset), and closes it in `on_unload`.
- `commands/`
  - `chat.py` – the unified `chat` command. Loads channel history, builds the OpenAI messages list, calls `call_acpbox`, persists the new user+assistant turns, and replies with `build_reply_text`.
  - `clear.py` – the unified `clearai` command (alias `clearchat`). Deletes all history rows for the current channel.
- `models/`
  - `conversation.py` – `AIConversation` SQLAlchemy model (row per turn, indexed on `(guild_id, channel_id, created_at)`).
- `utils.py` – acpbox HTTP client (`call_acpbox`), history helpers (`load_history`, `append_turn`, `clear_history`), and reply formatting (`build_reply_text`). Typed exceptions map each failure category to a user-facing error embed.
- `config.py` – constants (endpoint path, Discord message limit, max prompt length, footer template).

## Commands
| Command | Description | Permission Node |
| --- | --- | --- |
| `/chat <message>` / `!chat <message>` | Send a message to the AI and reply with the response. | `basic.ai.chat` |
| `/clearai` / `!clearai` / `!clearchat` | Clear this channel's retained AI history. | `basic.ai.clear` |

## Configuration
All settings live on the global `config.settings.settings` singleton (env-backed):

| Env var | Field | Default | Notes |
| --- | --- | --- | --- |
| `ACPBOX_URL` | `acpbox_url` | `None` | **Required** when the `ai` plugin is enabled. Base URL of the deployed acpbox. |
| `AI_MODEL` | `ai_model` | `None` | **Required** when the `ai` plugin is enabled. Model name sent in the Chat Completions body. |
| `AI_API_KEY` | `ai_api_key` | `None` | Optional bearer token sent as `Authorization: Bearer <key>`. |
| `AI_SYSTEM_PROMPT` | `ai_system_prompt` | helpful assistant prompt | Prepended to every request as the system message. |
| `AI_MAX_TOKENS` | `ai_max_tokens` | `1000` | `max_tokens` in the Chat Completions request. |
| `AI_TEMPERATURE` | `ai_temperature` | `0.7` | `temperature` in the Chat Completions request. |
| `AI_MEMORY_TURNS` | `ai_memory_turns` | `10` | Number of prior user+assistant turns retained per channel. |
| `AI_REQUEST_TIMEOUT` | `ai_request_timeout` | `30` | Total HTTP timeout in seconds for acpbox calls. |

The plugin appends `/v1/chat/completions` to `ACPBOX_URL` automatically.

## Development Guidelines
- Always guard acpbox calls with `if plugin.session is None` and surface a configuration error rather than crashing.
- Reuse `plugin.db_session()` for all persistence operations.
- Map acpbox failures through the typed exceptions in `utils.py` (`AcpboxUnreachableError`, `AcpboxRateLimitError`, `AcpboxHTTPError`, `AcpboxEmptyChoicesError`) so error embeds stay consistent.
- Prefer `plugin.smart_respond` for outputs so slash/prefix parity is preserved.
- Reuse `plugin.respond_error` / `plugin.respond_success` for error and confirmation embeds.
- Run plugin tests after changes: `uv run pytest tests/unit/plugins/ai`.

## Troubleshooting
- **`chat` returns "AI service is not configured"**: `ACPBOX_URL` or `AI_MODEL` is unset. Set both in `.env` and restart.
- **"AI service is unreachable"**: acpbox is down or the URL is wrong; check connectivity and `AI_REQUEST_TIMEOUT`.
- **"AI service is rate-limited"**: acpbox returned 429; retry shortly or raise upstream limits.
- **History grows unexpectedly**: `AI_MEMORY_TURNS` bounds retained turns; older rows are pruned on each new turn.
