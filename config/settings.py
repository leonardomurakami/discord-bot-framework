from pydantic import Field
from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    discord_token: str = Field(..., description="Discord bot token")
    database_url: str = Field(default="sqlite:///data/bot.db", description="Database connection URL")

    bot_prefix: str = Field(default="!", description="Command prefix")
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="DEBUG", description="Logging level")

    # Plugin configuration
    enabled_plugins: list[str] = Field(
        default=["admin", "fun", "moderation", "help", "utility", "music", "links"],
        description="List of enabled plugins",
    )
    plugin_directories: list[str] = Field(
        default=["plugins", "bot/plugins"],
        description="Directories to scan for plugins",
    )

    # Development settings
    debug: bool = Field(default=False, description="Enable debug mode")

    # Web interface
    web_port: int = Field(default=7000, description="Web interface port")
    web_host: str = Field(default="0.0.0.0", description="Web interface host")
    web_secret_key: str = Field(..., description="Secret key for sessions")

    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    redis_session_prefix: str = Field(default="bot_session:", description="Redis session key prefix")
    redis_session_ttl: int = Field(default=86400, description="Session TTL in seconds (24 hours)")

    # Discord OAuth2
    discord_client_id: str | None = Field(default=None, description="Discord OAuth2 client ID")
    discord_client_secret: str | None = Field(default=None, description="Discord OAuth2 client secret")
    discord_redirect_uri: str = Field(default="http://localhost:8080/auth/callback", description="OAuth2 redirect URI")

    # Lavalink settings
    lavalink_host: str = Field(default="lavalink", description="Lavalink server host")
    lavalink_port: int = Field(default=2333, description="Lavalink server port")
    lavalink_password: str = Field(default="youshallnotpass", description="Lavalink server password")
    lavalink_secure: bool = Field(default=False, description="Use secure connection to Lavalink")

    # Music plugin settings
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = BotSettings()
