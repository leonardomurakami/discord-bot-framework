## MODIFIED Requirements

### Requirement: Plugin configuration
The framework SHALL provide configurable lists of enabled plugins and plugin directories.

#### Scenario: Use default enabled plugins
- **WHEN** no ENABLED_PLUGINS environment variable is set
- **THEN** the `enabled_plugins` field defaults to `["admin", "fun", "games", "moderation", "help", "utility", "music", "links", "ai"]`

#### Scenario: Use default plugin directories
- **WHEN** no PLUGIN_DIRECTORIES environment variable is set
- **THEN** the `plugin_directories` field defaults to `["plugins", "bot/plugins"]`

## ADDED Requirements

### Requirement: AI service configuration
The framework SHALL provide configurable settings for the AI chat plugin covering the acpbox endpoint, model selection, authentication, generation parameters, and memory limits.

#### Scenario: Configure acpbox endpoint and model
- **WHEN** ACPBOX_URL and AI_MODEL environment variables are set
- **THEN** the `acpbox_url` and `ai_model` fields use the provided values for AI chat requests

#### Scenario: Use default acpbox settings
- **WHEN** no ACPBOX_URL or AI_MODEL environment variables are set
- **THEN** `acpbox_url` defaults to `None` and `ai_model` defaults to `glm-5-2`, and the AI plugin SHALL refuse to load or SHALL respond with a configuration error when `acpbox_url` is unset

#### Scenario: Configure optional API key
- **WHEN** AI_API_KEY is set
- **THEN** the `ai_api_key` field uses the provided value and the AI plugin SHALL send it as a bearer token to the acpbox endpoint
- **WHEN** AI_API_KEY is not set
- **THEN** `ai_api_key` defaults to `None` and the AI plugin SHALL omit the authorization header

#### Scenario: Configure system prompt
- **WHEN** AI_SYSTEM_PROMPT is set
- **THEN** the `ai_system_prompt` field uses the provided value as the system message prepended to every chat request
- **WHEN** AI_SYSTEM_PROMPT is not set
- **THEN** `ai_system_prompt` defaults to a helpful assistant prompt

#### Scenario: Configure generation parameters
- **WHEN** AI_MAX_TOKENS and AI_TEMPERATURE environment variables are set
- **THEN** the `ai_max_tokens` and `ai_temperature` fields use the provided values for Chat Completions requests
- **WHEN** AI_MAX_TOKENS and AI_TEMPERATURE are not set
- **THEN** `ai_max_tokens` defaults to `1000` and `ai_temperature` defaults to `0.7`

#### Scenario: Configure memory and timeout
- **WHEN** AI_MEMORY_TURNS and AI_REQUEST_TIMEOUT environment variables are set
- **THEN** the `ai_memory_turns` and `ai_request_timeout` fields use the provided values for conversation history retention and HTTP request timeout
- **WHEN** AI_MEMORY_TURNS and AI_REQUEST_TIMEOUT are not set
- **THEN** `ai_memory_turns` defaults to `10` and `ai_request_timeout` defaults to `30`
