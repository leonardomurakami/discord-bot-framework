## Purpose
Provides an AI chat plugin that lets Discord members converse with an OpenAI-compatible model (acpbox) via slash and prefix commands, with per-channel conversation memory, history clearing, configurable model and generation parameters, and graceful error handling.

## ADDED Requirements

### Requirement: Chat Command
The plugin SHALL provide a unified `chat` command invocable as both `/chat` (slash) and `!chat` (prefix), accepting a required free-text `message` argument containing the user's prompt.

#### Scenario: Invoke chat via slash
- **WHEN** a user with the `basic.ai.chat` permission invokes `/chat message: "What is Hikari?"`
- **THEN** the plugin SHALL send the prompt to the acpbox OpenAI-compatible Chat Completions endpoint and reply in the same channel with the assistant's response text

#### Scenario: Invoke chat via prefix
- **WHEN** a user with the `basic.ai.chat` permission invokes `!chat What is Hikari?`
- **THEN** the plugin SHALL parse the entire trailing text as the `message` argument, send the prompt to the acpbox endpoint, and reply in the same channel with the assistant's response text

#### Scenario: Missing message argument
- **WHEN** a user invokes `/chat` or `!chat` without providing a message
- **THEN** the plugin SHALL respond with an error indicating a message is required and not call the acpbox endpoint

#### Scenario: Permission denied
- **WHEN** a user lacking the `basic.ai.chat` permission invokes `chat`
- **THEN** the plugin SHALL deny access with an ephemeral error message and not call the acpbox endpoint

### Requirement: OpenAI-Compatible API Integration
The plugin SHALL call the acpbox endpoint at `{acpbox_url}/v1/chat/completions` using an HTTP client, sending a Chat Completions request with the configured model, message history, and generation parameters, and SHALL parse the assistant message from the first choice in the response.

#### Scenario: Successful API call
- **WHEN** the plugin sends a well-formed Chat Completions request and the endpoint returns a 2xx response with at least one choice
- **THEN** the plugin SHALL extract the assistant message content from `choices[0].message.content` and reply with it

#### Scenario: API key sent when configured
- **WHEN** `ai_api_key` is set in configuration and the plugin makes a request to the acpbox endpoint
- **THEN** the plugin SHALL include an `Authorization: Bearer <ai_api_key>` header in the request

#### Scenario: No API key header when unconfigured
- **WHEN** `ai_api_key` is not set in configuration and the plugin makes a request to the acpbox endpoint
- **THEN** the plugin SHALL omit the `Authorization` header

#### Scenario: Request body shape
- **WHEN** the plugin builds the Chat Completions request body
- **THEN** the body SHALL include `model` set to `ai_model`, `messages` containing the system prompt followed by retained history and the new user prompt, `max_tokens` set to `ai_max_tokens`, and `temperature` set to `ai_temperature`

### Requirement: Per-Channel Conversation Memory
The plugin SHALL retain conversation history per guild channel so users can hold ongoing threads, persisting up to `ai_memory_turns` turns (a turn is one user message plus one assistant reply) in a database table and including the retained history in subsequent requests.

#### Scenario: First message in a channel
- **WHEN** a user sends the first `chat` message in a channel with no prior history
- **THEN** the plugin SHALL send only the system prompt and the new user message to the endpoint, and after the response, SHALL store the user message and assistant reply as a new history entry for that channel

#### Scenario: Subsequent message uses retained history
- **WHEN** a user sends a `chat` message in a channel that has prior history
- **THEN** the plugin SHALL load the stored turns for that channel (up to `ai_memory_turns`), append them to the request messages between the system prompt and the new user prompt, and after the response, SHALL store the new user message and assistant reply

#### Scenario: History truncation to configured turn limit
- **WHEN** a channel has more than `ai_memory_turns` stored turns
- **THEN** the plugin SHALL include only the most recent `ai_memory_turns` turns in the request and SHALL prune older stored turns so the persisted history does not grow unbounded

#### Scenario: Memory survives bot restart
- **WHEN** the bot restarts and a user sends a `chat` message in a channel with stored history
- **THEN** the plugin SHALL load the persisted history from the database and include it in the request

### Requirement: Clear History Command
The plugin SHALL provide a unified `clearai` command invocable as both `/clearai` and `!clearai` (with alias `!clearchat`) that deletes the retained conversation history for the current channel.

#### Scenario: Clear history successfully
- **WHEN** a user with the `basic.ai.clear` permission invokes `clearai` in a channel that has stored history
- **THEN** the plugin SHALL delete all history entries for that channel from the database and respond with a confirmation message

#### Scenario: Clear history when none exists
- **WHEN** a user with the `basic.ai.clear` permission invokes `clearai` in a channel with no stored history
- **THEN** the plugin SHALL respond indicating there was no history to clear

#### Scenario: Clear history permission denied
- **WHEN** a user lacking the `basic.ai.clear` permission invokes `clearai`
- **THEN** the plugin SHALL deny access with an ephemeral error message and not modify the database

### Requirement: HTTP Client Lifecycle
The plugin SHALL maintain a single HTTP client session created during plugin load and closed during plugin unload to avoid leaking connections.

#### Scenario: Initialize HTTP session on load
- **WHEN** the plugin loads
- **THEN** the plugin SHALL create an aiohttp ClientSession with a request timeout set to `ai_request_timeout`

#### Scenario: Close HTTP session on unload
- **WHEN** the plugin unloads
- **THEN** the plugin SHALL close the aiohttp ClientSession gracefully

#### Scenario: Reject API calls before load
- **WHEN** the `chat` command is invoked before the plugin's HTTP session is initialized
- **THEN** the plugin SHALL respond with a service-unavailable error and not attempt the request

### Requirement: Error Handling
The plugin SHALL catch and surface errors from the acpbox endpoint and the HTTP client without crashing, returning a user-facing error embed describing the failure category.

#### Scenario: Endpoint unreachable
- **WHEN** the acpbox endpoint cannot be reached (connection error or timeout)
- **THEN** the plugin SHALL respond with an error embed indicating the AI service is unreachable and log the exception

#### Scenario: Non-success HTTP status
- **WHEN** the endpoint returns a non-2xx status code
- **THEN** the plugin SHALL respond with an error embed that includes the status code and a truncated error body, and log the full response

#### Scenario: Rate limited
- **WHEN** the endpoint returns HTTP 429
- **THEN** the plugin SHALL respond with an error embed indicating the AI service is rate-limited and suggesting the user try again shortly

#### Scenario: Empty choices in response
- **WHEN** the endpoint returns a 2xx response with an empty `choices` array
- **THEN** the plugin SHALL respond with an error embed indicating the AI returned no response

#### Scenario: Over-length prompt
- **WHEN** the user's `message` argument exceeds a configured maximum character limit
- **THEN** the plugin SHALL respond with an error embed indicating the prompt is too long and not call the endpoint

### Requirement: Reply Formatting
The plugin SHALL reply with the assistant response as a plain message in the same channel, truncated to Discord's message length limit, with a footer crediting the configured model when the response is not ephemeral.

#### Scenario: Normal-length reply
- **WHEN** the assistant response is within Discord's message length limit
- **THEN** the plugin SHALL send the response text as a single message with a footer indicating the model name

#### Scenario: Over-length reply
- **WHEN** the assistant response exceeds Discord's message length limit
- **THEN** the plugin SHALL truncate the response to fit and append an ellipsis indicator, sending it as a single message

### Requirement: Permission Node Declaration
The plugin SHALL declare the `basic.ai.chat` and `basic.ai.clear` permission nodes in its `PLUGIN_METADATA["permissions"]` so the PermissionManager seeds them during initialization.

#### Scenario: Permissions seeded on initialization
- **WHEN** the bot starts and the `ai` plugin is loaded
- **THEN** the PermissionManager SHALL create `basic.ai.chat` and `basic.ai.clear` permission records and grant them by default to all users (per the `basic.*` default-allow rule)

### Requirement: Database Model Registration
The plugin SHALL register a conversation history model via `DatabaseMixin` so its table is created during startup, storing per-channel turns with guild id, channel id, role (user/assistant), content, and timestamp.

#### Scenario: Register model on load
- **WHEN** the plugin loads
- **THEN** the plugin SHALL register the conversation history model with the database manager so `create_plugin_tables()` creates the table

#### Scenario: Table created on startup
- **WHEN** the bot initializes systems after the plugin loads
- **THEN** the conversation history table SHALL exist in the database
