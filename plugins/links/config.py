from pydantic import Field
from pydantic_settings import BaseSettings


class LinksSettings(BaseSettings):
    """Configuration for the Links plugin."""

    default_links: dict[str, str] = Field(
        default={
            "github": "https://github.com/leonardomurakami/discord-bot-framework",
            "panel": "http://bot.murakams.com",
            "docs": "https://docs.murakams.com/discord-bot-framework",
            "support": "https://discord.gg/murakamih",
        },
        description="Default links available to all guilds",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "LINKS_"
        case_sensitive = False
        extra = "ignore"


# Plugin settings instance
links_settings = LinksSettings()
