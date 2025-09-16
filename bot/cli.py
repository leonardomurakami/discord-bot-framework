import typer
import asyncio
import logging
from pathlib import Path
from typing import Optional, List

from config.settings import settings
from bot.core import DiscordBot

app = typer.Typer(
    name="discord-bot",
    help="Modular Discord Bot Framework",
    add_completion=False,
)


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


@app.command()
def run(
    dev: bool = typer.Option(False, "--dev", help="Run in development mode"),
    log_level: Optional[str] = typer.Option(None, "--log-level", help="Set log level"),
) -> None:
    """Run the Discord bot."""
    if dev:
        import os
        os.environ["ENVIRONMENT"] = "development"
        os.environ["HOT_RELOAD"] = "true"

    if log_level:
        import os
        os.environ["LOG_LEVEL"] = log_level

    setup_logging(log_level or settings.log_level)

    bot = DiscordBot()

    # Bot ready to run

    bot.run()


@app.command()
def init(
    directory: Optional[str] = typer.Option(None, help="Directory to initialize")
) -> None:
    """Initialize a new bot project."""
    target_dir = Path(directory) if directory else Path.cwd()

    if not target_dir.exists():
        target_dir.mkdir(parents=True)

    # Create basic structure
    (target_dir / "plugins").mkdir(exist_ok=True)
    (target_dir / "data").mkdir(exist_ok=True)

    # Create .env file
    env_file = target_dir / ".env"
    if not env_file.exists():
        env_content = """# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
BOT_PREFIX=!
DATABASE_URL=sqlite:///data/bot.db
ENVIRONMENT=development
LOG_LEVEL=INFO
"""
        env_file.write_text(env_content)

    typer.echo(f"✅ Bot project initialized in {target_dir}")


@app.command()
def plugins(
    action: str = typer.Argument(help="Action: list, enable, disable"),
    plugin_name: Optional[str] = typer.Option(None, help="Plugin name"),
) -> None:
    """Manage plugins."""
    if action == "list":
        typer.echo("📦 Available Plugins:")
        for directory in settings.plugin_directories:
            plugin_dir = Path(directory)
            if plugin_dir.exists():
                for plugin_path in plugin_dir.iterdir():
                    if plugin_path.is_dir() and (plugin_path / "__init__.py").exists():
                        enabled = "✅" if plugin_path.name in settings.enabled_plugins else "❌"
                        typer.echo(f"  {enabled} {plugin_path.name}")
    else:
        typer.echo("Plugin management from CLI is not yet implemented.")
        typer.echo("Use the bot's admin commands to manage plugins at runtime.")


@app.command()
def db(
    action: str = typer.Argument(help="Action: create, migrate, reset"),
) -> None:
    """Database management commands."""
    async def run_db_command():
        from bot.database import db_manager

        if action == "create":
            await db_manager.create_tables()
            typer.echo("✅ Database tables created")
        elif action == "reset":
            confirm = typer.confirm("⚠️  This will delete all data. Continue?")
            if confirm:
                await db_manager.drop_tables()
                await db_manager.create_tables()
                typer.echo("✅ Database reset completed")
        else:
            typer.echo(f"Unknown action: {action}")

    asyncio.run(run_db_command())


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()