## Why

The framework ships plugins for fun, games, moderation, music, and utility, but has no way for guild members to interact with an AI model from within Discord. An internal `acpbox` service exposes an OpenAI-compatible endpoint that is already deployed; wiring a bot command to it lets members ask questions, brainstorm, and get instant AI replies without leaving the conversation. Adding it now leverages the existing plugin system, permission model, and per-channel persistence patterns so the feature lands with minimal new infrastructure.

## What Changes

- Add a new first-party `ai` plugin (`plugins/ai/`) that registers a unified `chat` command, invocable as both `/chat` (slash) and `!chat` (prefix), taking a free-text `message` argument.
- The plugin calls the acpbox OpenAI-compatible Chat Completions endpoint (`POST {acpbox_url}/v1/chat/completions`) using an `aiohttp.ClientSession` managed over the plugin lifecycle, then replies with the assistant message content.
- Introduce per-channel conversation memory: the last N turns per guild channel are retained in a new `AIConversation` database model so users can hold ongoing threads in a channel. A `!clearai` (and `/clearai`) command resets a channel's history.
- Add a `basic.ai.chat` permission node (open to all by default, consistent with `basic.*` seeding) and `basic.ai.clear` for clearing history.
- Extend `config/settings.py` with AI-related fields: `acpbox_url`, `ai_model`, `ai_api_key` (optional), `ai_system_prompt`, `ai_max_tokens`, `ai_temperature`, `ai_memory_turns`, `ai_request_timeout`. Add `ai` to the default `enabled_plugins` list.
- Add an aiohttp client session created in `on_load` and closed in `on_unload` to avoid leaking connections (matches the pattern used by `fun`, `games`, and `utility`).
- Handle errors gracefully: endpoint unreachable, non-2xx responses, rate limits, empty choices, and over-length prompts return a friendly ephemeral/user-facing error embed instead of crashing.

## Capabilities

### New Capabilities
- `plugins/ai`: AI chat plugin that lets members talk to an OpenAI-compatible model (acpbox) via `/chat` and `!chat`, with per-channel conversation memory, history clearing, configurable model/system prompt/limits, and graceful error handling.

### Modified Capabilities
- `framework/configuration`: Adds AI-related settings fields (`acpbox_url`, `ai_model`, `ai_api_key`, `ai_system_prompt`, `ai_max_tokens`, `ai_temperature`, `ai_memory_turns`, `ai_request_timeout`) and includes `ai` in the default `enabled_plugins` list.

## Impact

- **New code**: `plugins/ai/` package (`__init__.py`, `plugin.py`, `config.py`, `commands/chat.py`, `commands/clear.py`, `models/__init__.py`, `models/conversation.py`, `utils.py`). Possibly `plugins/ai/web/` is out of scope for this change (no web panel).
- **Config**: `config/settings.py` gains AI fields; `.env.example` documents the new `ACPBOX_URL`, `AI_MODEL`, `AI_API_KEY`, `AI_SYSTEM_PROMPT`, `AI_MAX_TOKENS`, `AI_TEMPERATURE`, `AI_MEMORY_TURNS`, `AI_REQUEST_TIMEOUT` variables.
- **Database**: New `AIConversation` model registered via `DatabaseMixin`; `db.create_plugin_tables()` creates the table on startup.
- **Permissions**: `basic.ai.chat` and `basic.ai.clear` nodes seeded by `PermissionManager.initialize()` from the plugin's `PLUGIN_METADATA["permissions"]`.
- **Dependencies**: Uses `aiohttp` (already a framework dependency for other plugins). No new third-party packages required; the OpenAI-compatible API is called directly over HTTP.
- **Tests**: New `tests/unit/plugins/ai/` suite covering command registration, argument parsing, API request shaping, memory truncation, history clearing, and error paths.
- **Docs**: `README.md` plugin list updated; `AGENTS.md` plugin tour mentions the `ai` plugin.
