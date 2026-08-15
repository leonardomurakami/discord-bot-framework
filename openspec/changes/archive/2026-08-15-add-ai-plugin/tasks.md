## 1. Configuration

- [x] 1.1 Add AI fields to `config/settings.py` `BotSettings`: `acpbox_url` (default `None`), `ai_model` (default `None`), `ai_api_key` (default `None`), `ai_system_prompt` (default a helpful-assistant string), `ai_max_tokens` (default `1000`), `ai_temperature` (default `0.7`), `ai_memory_turns` (default `10`), `ai_request_timeout` (default `30`). Use Pydantic field metadata so each loads from its env var (`ACPBOX_URL`, `AI_MODEL`, `AI_API_KEY`, `AI_SYSTEM_PROMPT`, `AI_MAX_TOKENS`, `AI_TEMPERATURE`, `AI_MEMORY_TURNS`, `AI_REQUEST_TIMEOUT`).
- [x] 1.2 Add `"ai"` to the default `enabled_plugins` list in `config/settings.py`.
- [x] 1.3 Document the new env vars in `.env.example` with comments noting `ACPBOX_URL` and `AI_MODEL` are required when the `ai` plugin is enabled.
- [x] 1.4 Add a unit test under `tests/unit/bot/` (or extend an existing settings test) asserting the new fields default correctly and load from environment variables.

## 2. Plugin scaffold

- [x] 2.1 Create `plugins/ai/__init__.py` exporting `AIAPlugin` (or `AIPlugin`) and declaring `PLUGIN_METADATA` with `name`, `version`, `author`, `description`, `dependencies: []`, and `permissions: ["basic.ai.chat", "basic.ai.clear"]`. Include a `setup(bot)` factory returning the plugin instance.
- [x] 2.2 Create `plugins/ai/config.py` with constants used by the plugin (default system prompt text, over-length prompt character limit, Discord message length limit reference, request path `/v1/chat/completions`).
- [x] 2.3 Create `plugins/ai/plugin.py` defining `AIPlugin(DatabaseMixin, BasePlugin)` that: in `__init__` calls `super().__init__(bot)` and `self.register_model(AIConversation)`; in `on_load` creates `self.session = aiohttp.ClientSession(timeout=...)` guarded by `acpbox_url`/`ai_model` presence (soft-fail with a warning log and skip session creation if unset); in `on_unload` closes `self.session` if present.
- [x] 2.4 Add a nested `AGENTS.md` at `plugins/ai/AGENTS.md` describing the plugin's layout, commands, permission nodes, config fields, and the acpbox integration (mirror the style of `plugins/fun/AGENTS.md` and `plugins/games/AGENTS.md`).

## 3. Database model

- [x] 3.1 Create `plugins/ai/models/__init__.py` exporting `AIConversation`.
- [x] 3.2 Create `plugins/ai/models/conversation.py` defining `AIConversation(Base)` with columns `id` (PK), `guild_id` (BigInteger, indexed), `channel_id` (BigInteger, indexed), `role` (String, `"user"` or `"assistant"`), `content` (Text), `created_at` (DateTime, server default now). Add an index on `(guild_id, channel_id, created_at)`.
- [x] 3.3 Add a unit test asserting the model registers with the database manager and that `create_plugin_tables()` creates the `ai_conversation` table (mirror the games plugin's model-registration test pattern).

## 4. AI client utility

- [x] 4.1 Create `plugins/ai/utils.py` with an async function `call_acpbox(session, settings, messages) -> str` that: builds the request body (`model`, `messages`, `max_tokens`, `temperature`), sets `Authorization: Bearer <ai_api_key>` only when `ai_api_key` is set, POSTs to `{settings.acpbox_url}/v1/chat/completions`, raises typed exceptions for timeout/connection error/non-2xx/429/empty-choices, and returns `choices[0].message.content` on success.
- [x] 4.2 Add a helper `load_history(db, guild_id, channel_id, memory_turns) -> list[dict]` that selects the last `2 * memory_turns` rows for the channel ordered by `created_at` ascending and returns them as `{"role": ..., "content": ...}` message dicts.
- [x] 4.3 Add a helper `append_turn(db, guild_id, channel_id, role, content, memory_turns)` that inserts a new row and prunes rows beyond `2 * memory_turns` for the channel in the same transaction.
- [x] 4.4 Add a helper `clear_history(db, guild_id, channel_id) -> int` that deletes all rows for the channel and returns the deleted count.
- [x] 4.5 Add a helper `build_reply_text(content, model_name) -> str` that truncates `content` to Discord's message limit (reserving room for the footer) and appends a model-crediting footer line.
- [x] 4.6 Add unit tests for `utils.py` covering: request body shape, auth header present/absent, success parsing, timeout/non-2xx/429/empty-choices error mapping, history load ordering, append+prune behavior, clear count, and reply truncation. Use `aiohttp` stubs/`aresponses` and an in-memory SQLite DB fixture.

## 5. Chat command

- [x] 5.1 Create `plugins/ai/commands/__init__.py` with a `setup_chat_commands(plugin)` factory returning the command callables (mirror `plugins/fun/commands/basic.py`).
- [x] 5.2 Create `plugins/ai/commands/chat.py` defining the unified `chat` command via `@command(name="chat", description="Chat with the AI", permission_node="basic.ai.chat", arguments=[CommandArgument("message", hikari.OptionType.STRING, "Your message to the AI", required=True)])`. The handler: rejects if `plugin.session` is None (service-unavailable error); rejects over-length prompts; loads channel history; builds `messages = [system_prompt] + history + [{"role":"user","content":message}]`; calls `call_acpbox`; appends the user and assistant turns; replies with `build_reply_text`. Wrap the whole flow in try/except mapping each error category to the spec'd error embed.
- [x] 5.3 Wire `setup_chat_commands` into `AIPlugin` so the commands are registered on `on_load` (follow the existing plugin's `_register_commands` pattern or the factory-attachment pattern used by `fun`).
- [x] 5.4 Add unit tests for the chat command: successful slash invocation, successful prefix invocation (trailing text becomes `message`), missing message argument, permission denied, session unavailable, over-length prompt, endpoint unreachable, non-2xx, 429, empty choices, history inclusion on second call, and history truncation after exceeding `ai_memory_turns`. Stub `call_acpbox` and the DB session.

## 6. Clear-history command

- [x] 6.1 Create `plugins/ai/commands/clear.py` defining the unified `clearai` command via `@command(name="clearai", description="Clear this channel's AI history", aliases=["clearchat"], permission_node="basic.ai.clear")` (no arguments). The handler calls `clear_history` for the current channel and responds with a confirmation or a "no history" message based on the deleted count.
- [x] 6.2 Wire `setup_clear_commands` (or extend the commands `__init__` factory) into `AIPlugin` registration.
- [x] 6.3 Add unit tests for `clearai`: successful clear with existing history, clear with no history, permission denied, and prefix alias `!clearchat` resolves to the same handler.

## 7. Integration & docs

- [x] 7.1 Run `uv run pytest tests/unit/plugins/ai` and ensure all new tests pass with coverage at or above the project's 70% threshold for the plugin.
- [x] 7.2 Run `uv run ruff check plugins/ai config/settings.py` and `uv run black --check plugins/ai config/settings.py` (135 char line length); fix any findings.
- [x] 7.3 Update `README.md` plugin list to include the `ai` plugin with its commands, permission nodes, and required env vars.
- [x] 7.4 Update the top-level `AGENTS.md` repository tour (section 2) to mention the `ai` first-party plugin alongside the existing plugin list.
- [x] 7.5 Manually verify (or add a smoke test) that with `ACPBOX_URL`/`AI_MODEL` unset the bot still starts, the `ai` plugin logs a soft-fail warning, and `!chat`/`/chat` return a configuration error rather than crashing.
