from pydantic import Field
from pydantic_settings import BaseSettings


class MusicSettings(BaseSettings):
    """Configuration for the Music plugin."""

    # Disconnect settings
    disconnect_timeout_seconds: int = Field(
        default=300,  # 5 minutes
        description="Time in seconds before bot disconnects from empty voice channel",
    )
    check_empty_interval_seconds: int = Field(
        default=5,
        description="Interval in seconds to check if voice channel is empty",
    )

    # UI timeouts
    control_view_timeout_seconds: int = Field(
        default=300,  # 5 minutes
        description="Timeout for music control buttons in seconds",
    )
    queue_view_timeout_seconds: int = Field(
        default=300,  # 5 minutes
        description="Timeout for queue view buttons in seconds",
    )

    # Queue limits
    max_queue_size: int = Field(
        default=100,
        description="Maximum number of tracks in queue",
    )
    max_search_results: int = Field(
        default=10,
        description="Maximum number of search results to display",
    )

    # History settings
    max_history_entries: int = Field(
        default=20,
        description="Maximum number of tracks to keep in history",
    )

    # Volume settings
    default_volume: int = Field(
        default=50,
        description="Default volume (0-100)",
    )
    max_volume: int = Field(
        default=100,
        description="Maximum allowed volume",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "MUSIC_"
        case_sensitive = False
        extra = "ignore"


# Plugin settings instance
music_settings = MusicSettings()
