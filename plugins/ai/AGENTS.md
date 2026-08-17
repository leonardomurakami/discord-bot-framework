# AI Plugin Guidelines

## Overview
- Lets Discord members chat with an AI model through an OpenAI-compatible Chat Completions endpoint (e.g. OpenRouter, OpenAI, or a local server like vLLM/llama.cpp).
- Exposes a unified `chat` command (`/chat` and `!chat`) accepting a free-text `message` argument.
- Maintains per-channel conversation memory (last N turns) in the `ai_conversation` table so users can hold ongoing threads.
- Provides a `clearai` command (`/clearai` and `!clearchat`) to reset a channel's history.
- Primary permission nodes:
  - `basic.ai.chat` – use the `chat` command (open to all by default).
  - `basic.ai.clear` – use the `clearai` command (open to all by default).

## Architecture
- `plugin.py` defines `AIPlugin(DatabaseMixin, BasePlugin)`. It registers the `AIConversation` model in `__init__`, creates an `aiohttp.ClientSession` in `on_load` (guarded by `AI_BASE_URL` presence — soft-fails with a warning if unset), and closes it in `on_unload`.
- `commands/`
  - `chat.py` – the unified `chat` command. Loads channel history, builds the OpenAI messages list, calls `call_ai`, persists the new user+assistant turns, and replies with `build_reply_text`.
  - `clear.py` – the unified `clearai` command (alias `clearchat`). Deletes all history rows for the current channel.
- `models/`
  - `conversation.py` – `AIConversation` SQLAlchemy model (row per turn, indexed on `(guild_id, channel_id, created_at)`).
- `utils.py` – OpenAI-compatible HTTP client (`call_ai`), history helpers (`load_history`, `append_turn`, `clear_history`), and reply formatting (`build_reply_text`). Typed exceptions map each failure category to a user-facing error embed.
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
| `AI_BASE_URL` | `ai_base_url` | `None` | **Required** when the `ai` plugin is enabled. Base URL of the OpenAI-compatible API (e.g. `https://openrouter.ai/api`, `https://api.openai.com`). |
| `AI_MODEL` | `ai_model` | `openai/gpt-4o-mini` | Model name sent in the Chat Completions body (e.g. `openai/gpt-4o-mini` for OpenRouter, `gpt-4o-mini` for OpenAI). |
| `AI_API_KEY` | `ai_api_key` | `None` | Bearer token sent as `Authorization: Bearer <key>`. Required by most hosted providers (OpenRouter, OpenAI); omit for local unauthenticated servers. |
| `AI_SYSTEM_PROMPT` | `ai_system_prompt` | helpful assistant prompt | Prepended to every request as the system message. |
| `AI_MAX_TOKENS` | `ai_max_tokens` | `1000` | `max_tokens` in the Chat Completions request. |
| `AI_TEMPERATURE` | `ai_temperature` | `0.7` | `temperature` in the Chat Completions request. |
| `AI_MEMORY_TURNS` | `ai_memory_turns` | `10` | Number of prior user+assistant turns retained per channel. |
| `AI_REQUEST_TIMEOUT` | `ai_request_timeout` | `30` | Total HTTP timeout in seconds for AI API calls. |

The plugin appends `/v1/chat/completions` to `AI_BASE_URL` automatically.

## Development Guidelines
- Always guard AI API calls with `if plugin.session is None` and surface a configuration error rather than crashing.
- Reuse `plugin.db_session()` for all persistence operations.
- Map AI API failures through the typed exceptions in `utils.py` (`AIClientUnreachableError`, `AIClientRateLimitError`, `AIClientHTTPError`, `AIClientEmptyChoicesError`) so error embeds stay consistent.
- Prefer `plugin.smart_respond` for outputs so slash/prefix parity is preserved.
- Reuse `plugin.respond_error` / `plugin.respond_success` for error and confirmation embeds.
- Run plugin tests after changes: `uv run pytest tests/unit/plugins/ai`.

## Troubleshooting
- **`chat` returns "AI service is not configured"**: `AI_BASE_URL` is unset. Set it in `.env` and restart.
- **"AI service is unreachable"**: the API endpoint is down or the URL is wrong; check connectivity and `AI_REQUEST_TIMEOUT`.
- **"AI service is rate-limited"**: the API returned 429; retry shortly or raise upstream limits.
- **Authentication errors (HTTP 401)**: verify `AI_API_KEY` is correct for your provider.
- **History grows unexpectedly**: `AI_MEMORY_TURNS` bounds retained turns; older rows are pruned on each new turn.
