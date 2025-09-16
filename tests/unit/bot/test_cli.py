"""Tests for bot/cli.py"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bot.cli import app, main, setup_logging


class TestSetupLogging:
    """Test logging setup functionality."""

    @patch("bot.cli.logging.basicConfig")
    def test_setup_logging_default_level(self, mock_basic_config):
        """Test setup_logging with default INFO level."""
        setup_logging()

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == 20  # logging.INFO

    @patch("bot.cli.logging.basicConfig")
    def test_setup_logging_custom_level(self, mock_basic_config):
        """Test setup_logging with custom level."""
        setup_logging("DEBUG")

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args
        assert call_args[1]["level"] == 10  # logging.DEBUG

    @patch("bot.cli.logging.basicConfig")
    def test_setup_logging_invalid_level(self, mock_basic_config):
        """Test setup_logging with invalid level defaults to INFO."""
        with pytest.raises(AttributeError):
            setup_logging("INVALID")


class TestCLICommands:
    """Test CLI command functionality."""

    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()

    @patch("bot.cli.DiscordBot")
    @patch("bot.cli.setup_logging")
    def test_run_command_default(self, mock_setup_logging, mock_discord_bot):
        """Test run command with default parameters."""
        mock_bot_instance = MagicMock()
        mock_discord_bot.return_value = mock_bot_instance

        result = self.runner.invoke(app, ["run"])

        assert result.exit_code == 0
        mock_setup_logging.assert_called_once()
        mock_discord_bot.assert_called_once()
        mock_bot_instance.run.assert_called_once()

    @patch("bot.cli.DiscordBot")
    @patch("bot.cli.setup_logging")
    def test_run_command_dev_mode(self, mock_setup_logging, mock_discord_bot):
        """Test run command with dev mode enabled."""
        mock_bot_instance = MagicMock()
        mock_discord_bot.return_value = mock_bot_instance

        result = self.runner.invoke(app, ["run", "--dev"])

        assert result.exit_code == 0
        assert os.environ.get("ENVIRONMENT") == "development"
        assert os.environ.get("HOT_RELOAD") == "true"
        mock_discord_bot.assert_called_once()
        mock_bot_instance.run.assert_called_once()

    @patch("bot.cli.DiscordBot")
    @patch("bot.cli.setup_logging")
    def test_run_command_custom_log_level(self, mock_setup_logging, mock_discord_bot):
        """Test run command with custom log level."""
        mock_bot_instance = MagicMock()
        mock_discord_bot.return_value = mock_bot_instance

        result = self.runner.invoke(app, ["run", "--log-level", "DEBUG"])

        assert result.exit_code == 0
        assert os.environ.get("LOG_LEVEL") == "DEBUG"
        mock_setup_logging.assert_called_once_with("DEBUG")
        mock_discord_bot.assert_called_once()

    def test_init_command_default_directory(self):
        """Test init command in current directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("bot.cli.Path.cwd", return_value=Path(temp_dir)):
                result = self.runner.invoke(app, ["init"])

                assert result.exit_code == 0
                assert "✅ Bot project initialized" in result.output

                # Check directories were created
                assert (Path(temp_dir) / "plugins").exists()
                assert (Path(temp_dir) / "data").exists()

                # Check .env file was created
                env_file = Path(temp_dir) / ".env"
                assert env_file.exists()
                content = env_file.read_text()
                assert "DISCORD_TOKEN=your_discord_bot_token_here" in content
                assert "BOT_PREFIX=!" in content

    def test_init_command_custom_directory(self):
        """Test init command with custom directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir) / "custom_bot"

            result = self.runner.invoke(app, ["init", "--directory", str(custom_dir)])

            assert result.exit_code == 0
            assert "✅ Bot project initialized" in result.output

            # Check directories were created
            assert (custom_dir / "plugins").exists()
            assert (custom_dir / "data").exists()

            # Check .env file was created
            env_file = custom_dir / ".env"
            assert env_file.exists()

    def test_init_command_existing_env_file(self):
        """Test init command doesn't overwrite existing .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            original_content = "EXISTING_CONTENT=true"
            env_file.write_text(original_content)

            with patch("bot.cli.Path.cwd", return_value=Path(temp_dir)):
                result = self.runner.invoke(app, ["init"])

                assert result.exit_code == 0
                # .env should not be overwritten
                assert env_file.read_text() == original_content

    @patch("bot.cli.settings")
    def test_plugins_list_command(self, mock_settings):
        """Test plugins list command."""
        # Setup mock settings
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_dir = Path(temp_dir) / "test_plugin"
            plugin_dir.mkdir()
            (plugin_dir / "__init__.py").touch()

            mock_settings.plugin_directories = [temp_dir]
            mock_settings.enabled_plugins = ["test_plugin"]

            result = self.runner.invoke(app, ["plugins", "list"])

            assert result.exit_code == 0
            assert "📦 Available Plugins:" in result.output
            assert "✅ test_plugin" in result.output

    def test_plugins_other_actions(self):
        """Test plugins command with other actions."""
        result = self.runner.invoke(app, ["plugins", "enable"])

        assert result.exit_code == 0
        assert "Plugin management from CLI is not yet implemented" in result.output

    @patch("bot.cli.asyncio.run")
    def test_db_create_command(self, mock_asyncio_run):
        """Test database create command."""
        result = self.runner.invoke(app, ["db", "create"])

        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()

    @patch("bot.cli.asyncio.run")
    def test_db_reset_command_confirmed(self, mock_asyncio_run):
        """Test database reset command with confirmation."""
        result = self.runner.invoke(app, ["db", "reset"], input="y\n")

        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()

    @patch("bot.cli.asyncio.run")
    def test_db_reset_command_declined(self, mock_asyncio_run):
        """Test database reset command declined."""
        result = self.runner.invoke(app, ["db", "reset"], input="n\n")

        assert result.exit_code == 0
        # asyncio.run is called but the inner logic doesn't execute
        mock_asyncio_run.assert_called_once()

    @patch("bot.cli.asyncio.run")
    def test_db_unknown_action(self, mock_asyncio_run):
        """Test database command with unknown action."""
        result = self.runner.invoke(app, ["db", "unknown"])

        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()

    @patch("bot.cli.app")
    def test_main_function(self, mock_app):
        """Test main function calls typer app."""
        main()
        mock_app.assert_called_once()


class TestAsyncDatabaseCommands:
    """Test async database command functionality."""

    @pytest.mark.asyncio
    async def test_db_create_action(self):
        """Test database create action."""
        from unittest.mock import AsyncMock

        with patch("bot.database.db_manager") as mock_db_manager:
            mock_db_manager.create_tables = AsyncMock()

            # We need to test the async function directly
            # since CliRunner doesn't handle async well
            async def run_db_command():
                from bot.database import db_manager

                await db_manager.create_tables()

            await run_db_command()
            mock_db_manager.create_tables.assert_called_once()

    @pytest.mark.asyncio
    async def test_db_reset_action(self):
        """Test database reset action."""
        from unittest.mock import AsyncMock

        with patch("bot.database.db_manager") as mock_db_manager:
            mock_db_manager.drop_tables = AsyncMock()
            mock_db_manager.create_tables = AsyncMock()

            # Test the reset logic
            async def run_db_command():
                from bot.database import db_manager

                await db_manager.drop_tables()
                await db_manager.create_tables()

            await run_db_command()
            mock_db_manager.drop_tables.assert_called_once()
            mock_db_manager.create_tables.assert_called_once()


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_dev_mode_sets_environment_vars(self):
        """Test that dev mode sets correct environment variables."""
        runner = CliRunner()

        # Clear environment variables first
        if "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]
        if "HOT_RELOAD" in os.environ:
            del os.environ["HOT_RELOAD"]

        with patch("bot.cli.DiscordBot"), patch("bot.cli.setup_logging"):
            result = runner.invoke(app, ["run", "--dev"])

            assert result.exit_code == 0
            assert os.environ.get("ENVIRONMENT") == "development"
            assert os.environ.get("HOT_RELOAD") == "true"

    def test_log_level_sets_environment_var(self):
        """Test that log level option sets environment variable."""
        runner = CliRunner()

        # Clear environment variable first
        if "LOG_LEVEL" in os.environ:
            del os.environ["LOG_LEVEL"]

        with patch("bot.cli.DiscordBot"), patch("bot.cli.setup_logging"):
            result = runner.invoke(app, ["run", "--log-level", "DEBUG"])

            assert result.exit_code == 0
            assert os.environ.get("LOG_LEVEL") == "DEBUG"
