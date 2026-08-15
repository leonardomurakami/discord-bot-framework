## Purpose
Provides a centralized Pydantic-based settings model with environment variable loading, defaults, and support for development and production configurations.

## Requirements

### Requirement: Pydantic settings model
The framework SHALL use Pydantic BaseSettings to define and validate configuration fields.

#### Scenario: Define required Discord token
- **WHEN** the BotSettings class is instantiated
- **THEN** the `discord_token` field is required (no default) and loaded from the DISCORD_TOKEN environment variable

### Requirement: Environment variable loading
The BotSettings class SHALL load configuration values from environment variables and a .env file.

#### Scenario: Load from .env file
- **WHEN** the settings singleton is created
- **THEN** Pydantic reads values from the `.env` file with UTF-8 encoding and case-insensitive matching

#### Scenario: Override with environment variable
- **WHEN** an environment variable is set that matches a settings field
- **THEN** the environment variable value takes precedence over the .env file value

### Requirement: Database URL configuration
The framework SHALL provide a configurable database URL with a default SQLite path.

#### Scenario: Use default database URL
- **WHEN** no DATABASE_URL environment variable is set
- **THEN** the `database_url` field defaults to `sqlite:///data/bot.db`

#### Scenario: Use custom database URL
- **WHEN** DATABASE_URL is set to a PostgreSQL connection string
- **THEN** the `database_url` field uses the provided value for PostgreSQL configuration

### Requirement: Bot prefix configuration
The framework SHALL provide a configurable command prefix with a default value.

#### Scenario: Use default bot prefix
- **WHEN** no BOT_PREFIX environment variable is set
- **THEN** the `bot_prefix` field defaults to `!`

### Requirement: Plugin configuration
The framework SHALL provide configurable lists of enabled plugins and plugin directories.

#### Scenario: Use default enabled plugins
- **WHEN** no ENABLED_PLUGINS environment variable is set
- **THEN** the `enabled_plugins` field defaults to `["admin", "fun", "games", "moderation", "help", "utility", "music", "links", "ai"]`

#### Scenario: Use default plugin directories
- **WHEN** no PLUGIN_DIRECTORIES environment variable is set
- **THEN** the `plugin_directories` field defaults to `["plugins", "bot/plugins"]`

### Requirement: Environment configuration
The framework SHALL support development and production environment modes.

#### Scenario: Use default environment
- **WHEN** no ENVIRONMENT environment variable is set
- **THEN** the `environment` field defaults to `"development"`

#### Scenario: Set production environment
- **WHEN** ENVIRONMENT is set to `"production"`
- **THEN** the `environment` field reflects the production mode for conditional behavior

### Requirement: Web interface configuration
The framework SHALL provide configurable web interface settings for host, port, and secret key.

#### Scenario: Configure web interface
- **WHEN** WEB_PORT, WEB_HOST, and WEB_SECRET_KEY environment variables are set
- **THEN** the `web_port`, `web_host`, and `web_secret_key` fields use the provided values for FastAPI configuration

### Requirement: Redis configuration
The framework SHALL provide configurable Redis connection settings with defaults.

#### Scenario: Use default Redis settings
- **WHEN** no Redis environment variables are set
- **THEN** `redis_url` defaults to `"redis://localhost:6379/0"`, `redis_session_prefix` defaults to `"bot_session:"`, and `redis_session_ttl` defaults to `86400`

### Requirement: Discord OAuth configuration
The framework SHALL provide optional Discord OAuth2 settings for web authentication.

#### Scenario: Configure Discord OAuth
- **WHEN** DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, and DISCORD_REDIRECT_URI are set
- **THEN** the `discord_client_id`, `discord_client_secret`, and `discord_redirect_uri` fields use the provided values for OAuth flow

#### Scenario: Optional OAuth fields
- **WHEN** Discord OAuth environment variables are not set
- **THEN** the OAuth fields default to None and OAuth authentication is disabled

### Requirement: Lavalink configuration
The framework SHALL provide configurable Lavalink server settings for music playback.

#### Scenario: Use default Lavalink settings
- **WHEN** no Lavalink environment variables are set
- **THEN** `lavalink_host` defaults to `"lavalink"`, `lavalink_port` defaults to `2333`, `lavalink_password` defaults to `"youshallnotpass"`, and `lavalink_secure` defaults to `False`

### Requirement: Spotify configuration
The framework SHALL provide optional Spotify client credentials for music plugin features.

#### Scenario: Configure Spotify integration
- **WHEN** SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set
- **THEN** the `spotify_client_id` and `spotify_client_secret` fields use the provided values for Spotify API access

### Requirement: Debug mode configuration
The framework SHALL provide a debug mode flag for development.

#### Scenario: Enable debug mode
- **WHEN** DEBUG is set to `"true"` or `"1"`
- **THEN** the `debug` field is set to True, enabling verbose logging and SQL echo

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

### Requirement: Global settings singleton
The framework SHALL provide a global settings instance for application-wide configuration access.

#### Scenario: Access global settings
- **WHEN** code imports `settings` from `config.settings`
- **THEN** a singleton BotSettings instance is returned with all configuration values loaded
