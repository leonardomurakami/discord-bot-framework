from pydantic import Field
from pydantic_settings import BaseSettings
from hikari import Color


class HelpSettings(BaseSettings):
    """Configuration for the Help plugin."""

    # View timeouts
    pagination_timeout_seconds: int = Field(
        default=300,  # 5 minutes
        description="Timeout for help pagination views in seconds",
    )

    # Display settings
    commands_per_page: int = Field(
        default=10,
        description="Number of commands to show per page in help",
    )
    embed_color: int = Field(
        default=0x5865F2,  # Discord blurple
        description="Default color for help embeds (hex value)",
    )

    # Content settings
    show_permissions: bool = Field(
        default=True,
        description="Whether to show required permissions in command help",
    )
    show_aliases: bool = Field(
        default=True,
        description="Whether to show command aliases in help",
    )
    show_plugin_info: bool = Field(
        default=True,
        description="Whether to show plugin information in help",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "HELP_"
        case_sensitive = False
        extra = "ignore"

    @property
    def embed_color_obj(self) -> Color:
        """Get the embed color as a Hikari Color object."""
        return Color(self.embed_color)


# Plugin settings instance
help_settings = HelpSettings()