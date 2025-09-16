from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    discord_token: str = Field(..., description="Discord bot token")
    database_url: str = Field(
        default="sqlite:///data/bot.db",
        description="Database connection URL"
    )

    bot_prefix: str = Field(default="!", description="Command prefix")
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="DEBUG", description="Logging level")

    # Plugin configuration
    enabled_plugins: List[str] = Field(
        default=['admin', 'fun', 'moderation', 'help', "utility"],
        description="List of enabled plugins"
    )
    plugin_directories: List[str] = Field(
        default=["plugins", "bot/plugins"],
        description="Directories to scan for plugins"
    )

    # Development settings
    debug: bool = Field(default=False, description="Enable debug mode")

    # Web interface (future)
    web_port: int = Field(default=8080, description="Web interface port")
    web_host: str = Field(default="0.0.0.0", description="Web interface host")

    # Music plugin settings
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = BotSettings()