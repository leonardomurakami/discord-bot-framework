## Context

The framework already supports a clean plugin pattern: a package under `plugins/<name>/` with `__init__.py` exporting `PLUGIN_METADATA` and a `setup` factory, a `BasePlugin` subclass in `plugin.py`, command modules that use the unified `@command` decorator from `bot.plugins.commands`, and optional `DatabaseMixin`/`WebPanelMixin` for persistence and web panels. Several existing plugins (`fun`, `games`, `utility`) manage an `aiohttp.ClientSession` in `on_load`/`on_unload` and guard API calls with `if plugin.session:`. See proposal.md for the motivation and the two affected capabilities (`plugins/ai` new, `framework/configuration` modified).

The acpbox service exposes an OpenAI-compatible Chat Completions endpoint already deployed; the bot only needs the base URL and model name to use it. No OpenAI SDK is required — the Chat Completions REST contract is simple enough to call directly with `aiohttp`, matching the pattern other plugins use for external HTTP.

## Goals / Non-Goals

**Goals:**
- Land a minimal, idiomatic `ai` plugin that follows existing plugin conventions (unified command decorator, `DatabaseMixin` for the conversation model, lifecycle-managed `aiohttp.ClientSession`, `basic.*` permission nodes).
- Keep the OpenAI-compatible call path thin and dependency-free so it works against any acpbox-style endpoint without a third-party SDK.
- Make conversation memory per-channel, persisted, and bounded by a configurable turn limit so history survives restarts without unbounded growth.

**Non-Goals:**
- No streaming responses (Discord gateway sends whole messages; streaming adds complexity for marginal UX gain here).
- No web panel for the AI plugin in this change (can be added later via `WebPanelMixin`).
- No multi-model routing, tool/function calling, or image inputs — text-in/text-out only.
- No cross-channel or per-user memory; memory is keyed by channel only, as confirmed during scoping.
- No token-usage accounting or cost tracking in this change.

## Decisions

### Decision: Direct `aiohttp` calls over an OpenAI SDK
**Choice:** Call `{acpbox_url}/v1/chat/completions` directly with `aiohttp` using the documented Chat Completions JSON shape.
**Rationale:** The framework already depends on `aiohttp` and every HTTP-using plugin follows this pattern. Adding the `openai` Python SDK would introduce a heavy dependency, its own async client, and version-coupling to OpenAI's surface area — none of which is needed for a single POST that returns `choices[0].message.content`. The acpbox endpoint is OpenAI-*compatible*, not guaranteed to track SDK versions, so a thin REST client is more robust.
**Alternatives considered:**
- `openai` SDK: rejected per above (dependency weight, compatibility risk).
- `httpx`: already not used elsewhere in the framework; `aiohttp` is the established choice.

### Decision: Per-channel memory keyed by `(guild_id, channel_id)` in a dedicated table
**Choice:** A single `AIConversation` table with rows per turn, columns `id, guild_id, channel_id, role, content, created_at`, indexed on `(guild_id, channel_id, created_at)`. History is loaded by selecting the last `2 * ai_memory_turns` rows (user+assistant pairs) ordered by `created_at`.
**Rationale:** Row-per-turn is simple to append, prune, and clear, and it reuses the `DatabaseMixin` + `register_model` pattern the `games` plugin uses. Keying by channel matches the confirmed scope (per-channel memory). Indexing on `(guild_id, channel_id, created_at)` keeps the common load query fast.
**Alternatives considered:**
- A single JSON blob per channel: simpler schema but harder to prune oldest turns atomically and harder to test.
- In-memory dict only: rejected because the spec requires history to survive bot restarts.

### Decision: Prune-on-write to enforce the turn limit
**Choice:** After appending a new turn, if the stored turn count for the channel exceeds `ai_memory_turns`, delete the oldest rows beyond the limit within the same DB transaction.
**Rationale:** Keeps the table bounded without a background sweep, and the prune happens exactly when a new turn is added — the only path that can grow history. The request itself reads only the most recent `ai_memory_turns` turns, so request shaping and pruning share one code path.
**Alternatives considered:**
- Periodic cleanup task: more moving parts, races with in-flight requests, and the bot would still need a per-channel cap on read.

### Decision: Unified `@command` decorator for both `chat` and `clearai`
**Choice:** Use `@command(name="chat", description=..., permission_node="basic.ai.chat", arguments=[CommandArgument("message", OptionType.STRING, "The message to send to the AI", required=True)])` and an analogous `clearai` command with `permission_node="basic.ai.clear"` and `aliases=["clearchat"]`.
**Rationale:** This is the framework's idiomatic way to get slash + prefix from one definition, with permission enforcement and argument parsing handled by `CommandRegistry`/`MessageCommandHandler`. For prefix mode, the trailing text after `!chat` becomes the `message` string argument via `ArgumentParserFactory`'s "last string consumes remaining text" rule — exactly the behavior the spec calls for.
**Alternatives considered:**
- Prefix-only via `prefix_only=True`: rejected per scoping (user chose slash + prefix).
- Two separate decorators: rejected — duplicates the handler.

### Decision: Configuration fields on the global `config.settings` singleton
**Choice:** Add `acpbox_url`, `ai_model`, `ai_api_key`, `ai_system_prompt`, `ai_max_tokens`, `ai_temperature`, `ai_memory_turns`, `ai_request_timeout` to `BotSettings` in `config/settings.py`, loaded from env vars (`ACPBOX_URL`, `AI_MODEL`, etc.). Default `acpbox_url` and `ai_model` to `None`; the plugin refuses to load (logs a warning and returns early from `on_load`) if either is unset.
**Rationale:** All other plugin config lives on the global settings singleton (e.g. `lavalink_*` for music), and the AGENTS handbook says secrets live in env vars, never hard-coded. Defaulting the endpoint to `None` and failing soft matches how the framework handles optional services (Redis sessions degrade gracefully; Lavalink is required only when music is enabled).
**Alternatives considered:**
- A plugin-local `config.py` with its own env reading: breaks the single-source-of-truth pattern the rest of the framework uses.
- Hard fail at bot startup if `acpbox_url` unset: too aggressive when `ai` is just one of many plugins; soft fail per-plugin is consistent with the plugin loader's "skip plugins that fail to load" behavior.

### Decision: Reply as plain text with a model-crediting footer, not an embed
**Choice:** Send the assistant response as a normal message (via `ctx.respond` for slash, `ctx.respond`/`rest.create_message` for prefix) with a small footer line crediting the configured `ai_model`. Truncate to Discord's 2000-char message limit.
**Rationale:** AI replies are free-form text of arbitrary length; embeds impose a 4096 description limit and add visual chrome that hurts readability for long prose. A plain message with a one-line footer is the least surprising UX. Truncation handles the over-length case simply.
**Alternatives considered:**
- Embed with description: rejected per above.
- Multi-message splitting for long replies: deferred (non-goal; truncation is simpler and sufficient for v1).

## Risks / Trade-offs

- **[Risk] acpbox endpoint latency blocks the command handler** → Mitigation: `ai_request_timeout` (default 30s) caps the wait; on timeout the plugin responds with a service-unavailable error embed. Future work could defer the reply, but v1 keeps the synchronous request/response UX.
- **[Risk] Per-channel memory leaks sensitive context across unrelated conversations in the same channel** → Mitigation: `clearai` lets users reset; memory is bounded to `ai_memory_turns`. Documented as a known trade-off of per-channel (vs per-user) memory, which the user explicitly chose.
- **[Risk] Unbounded prompt growth if `ai_memory_turns` is set high with long messages** → Mitigation: the over-length-prompt guard caps the *new* user message; a future enhancement can count tokens, but v1 relies on the turn limit plus `ai_max_tokens` on the response side.
- **[Risk] acpbox returns non-OpenAI-shaped JSON** → Mitigation: the parser keys only on `choices[0].message.content` and treats missing/empty choices as an error scenario (spec covers "empty choices"). Unexpected shapes surface as the generic non-2xx/parse error path.
- **[Trade-off] No streaming** → Simpler implementation; users wait for the full reply. Acceptable for v1 and reversible later.
- **[Trade-off] Soft-fail when `acpbox_url` unset** → The `ai` plugin loads but its commands return a configuration error. This avoids breaking bot startup for deployments that didn't configure acpbox, at the cost of a slightly worse first-run experience. Documented in `.env.example`.

## Migration Plan

1. Merge the new `plugins/ai/` package, the `config/settings.py` field additions, and the `ai` entry in `enabled_plugins` defaults.
2. On next bot start, `PluginLoader` discovers `ai`, `DatabaseMixin.register_model` registers `AIConversation`, and `db.create_plugin_tables()` creates the new table — no manual migration needed (additive table creation only).
3. `PermissionManager.initialize()` seeds `basic.ai.chat` and `basic.ai.clear` from `PLUGIN_METADATA["permissions"]`; both are granted to all users by the existing `basic.*` default-allow rule.
4. Deployments that don't set `ACPBOX_URL`/`AI_MODEL` see the plugin load with a warning and its commands return a config error — no crash, no broken startup.
5. **Rollback:** remove `ai` from `enabled_plugins` (or delete the `plugins/ai/` package). The `AIConversation` table can be dropped with `make db-reset` or left in place (it's unused). No data migration is required to revert.

## Open Questions

None. All material scope questions (command style, memory model, permissions, config fields) were resolved during scoping. The remaining details (exact default system prompt text, exact over-length prompt character limit) are implementation details that don't change the specs, approach, or task breakdown and can be decided during implementation.
