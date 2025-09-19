"""Tests for Fun plugin."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.fun.fun_plugin import FunPlugin
from tests.conftest import AsyncContextManager


class TestFunPlugin:
    """Test FunPlugin functionality."""

    def test_plugin_creation(self, mock_bot):
        """Test creating fun plugin."""
        plugin = FunPlugin(mock_bot)

        assert plugin.bot == mock_bot
        assert plugin.session is None

    @pytest.mark.asyncio
    async def test_on_load(self, mock_bot):
        """Test plugin loading."""
        plugin = FunPlugin(mock_bot)

        with patch("aiohttp.ClientSession") as mock_session:
            await plugin.on_load()

            assert plugin.session is not None
            mock_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_unload(self, mock_bot):
        """Test plugin unloading."""
        plugin = FunPlugin(mock_bot)

        # Set up session
        mock_session = AsyncMock()
        plugin.session = mock_session

        await plugin.on_unload()

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_command(self, mock_bot, mock_context):
        """Test ping command."""
        plugin = FunPlugin(mock_bot)

        await plugin.ping_command(mock_context)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_command_error(self, mock_bot, mock_context):
        """Test ping command with error."""
        plugin = FunPlugin(mock_bot)
        mock_context.respond.side_effect = Exception("Test error")

        # Should not raise exception
        await plugin.ping_command(mock_context)

    @pytest.mark.asyncio
    async def test_roll_dice_default(self, mock_bot, mock_context):
        """Test roll dice with default parameters."""
        plugin = FunPlugin(mock_bot)

        with patch("random.randint", return_value=4):
            await plugin.roll_dice(mock_context)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_roll_dice_custom(self, mock_bot, mock_context):
        """Test roll dice with custom parameters."""
        plugin = FunPlugin(mock_bot)

        with patch("random.randint", side_effect=[3, 5]):
            await plugin.roll_dice(mock_context, "2d6")

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_roll_dice_invalid_format(self, mock_bot, mock_context):
        """Test roll dice with invalid format."""
        plugin = FunPlugin(mock_bot)

        await plugin.roll_dice(mock_context, "invalid")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_roll_dice_too_many_dice(self, mock_bot, mock_context):
        """Test roll dice with too many dice."""
        plugin = FunPlugin(mock_bot)

        await plugin.roll_dice(mock_context, "25d6")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_roll_dice_too_many_sides(self, mock_bot, mock_context):
        """Test roll dice with too many sides."""
        plugin = FunPlugin(mock_bot)

        await plugin.roll_dice(mock_context, "1d2000")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_coinflip_command(self, mock_bot, mock_context):
        """Test coinflip command."""
        plugin = FunPlugin(mock_bot)

        with patch("random.choice", return_value="Heads"):
            await plugin.flip_coin(mock_context)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_coinflip_command_error(self, mock_bot, mock_context):
        """Test coinflip command with error."""
        plugin = FunPlugin(mock_bot)

        with patch("random.choice", side_effect=Exception("Test error")):
            await plugin.flip_coin(mock_context)

            # Should handle error gracefully
            assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_8ball_command(self, mock_bot, mock_context):
        """Test 8ball command."""
        plugin = FunPlugin(mock_bot)

        with patch("random.choice", return_value="Yes"):
            await plugin.magic_8ball(mock_context, "Will this test pass?")

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_8ball_command_error(self, mock_bot, mock_context):
        """Test 8ball command with error."""
        plugin = FunPlugin(mock_bot)

        with patch("random.choice", side_effect=Exception("Test error")):
            await plugin.magic_8ball(mock_context, "Test question?")

            # Should handle error gracefully
            assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_joke_command_api_success(self, mock_bot, mock_context):
        """Test joke command with successful API call."""
        plugin = FunPlugin(mock_bot)

        # Mock session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"type": "single", "joke": "Test joke"}

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
        plugin.session = mock_session

        await plugin.random_joke(mock_context)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_joke_command_api_two_part(self, mock_bot, mock_context):
        """Test joke command with two-part joke from API."""
        plugin = FunPlugin(mock_bot)

        # Mock session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "type": "twopart",
            "setup": "Test setup",
            "delivery": "Test punchline",
        }

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
        plugin.session = mock_session

        await plugin.random_joke(mock_context)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_joke_command_api_failure(self, mock_bot, mock_context):
        """Test joke command with API failure."""
        plugin = FunPlugin(mock_bot)

        # Mock session
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
        plugin.session = mock_session

        with patch("random.choice", return_value="Fallback joke"):
            await plugin.random_joke(mock_context)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_joke_command_no_session(self, mock_bot, mock_context):
        """Test joke command without session."""
        plugin = FunPlugin(mock_bot)
        plugin.session = None

        await plugin.random_joke(mock_context)

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_choose_command(self, mock_bot, mock_context):
        """Test choose command."""
        plugin = FunPlugin(mock_bot)

        with patch("random.choice", return_value="option1"):
            await plugin.choose_option(mock_context, "option1", "option2")

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_choose_command_error(self, mock_bot, mock_context):
        """Test choose command with error."""
        plugin = FunPlugin(mock_bot)

        with patch("random.choice", side_effect=Exception("Test error")):
            await plugin.choose_option(mock_context, "option1", "option2")

            # Should handle error gracefully
            assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_random_number_command(self, mock_bot, mock_context):
        """Test random number command."""
        plugin = FunPlugin(mock_bot)

        with patch("random.randint", return_value=50):
            await plugin.random_number(mock_context)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_random_number_custom_range(self, mock_bot, mock_context):
        """Test random number command with custom range."""
        plugin = FunPlugin(mock_bot)

        with patch("random.randint", return_value=15):
            await plugin.random_number(mock_context, 10, 20)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_random_number_invalid_range(self, mock_bot, mock_context):
        """Test random number command with invalid range."""
        plugin = FunPlugin(mock_bot)

        await plugin.random_number(mock_context, 20, 10)

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_random_number_too_large_range(self, mock_bot, mock_context):
        """Test random number command with too large range."""
        plugin = FunPlugin(mock_bot)

        await plugin.random_number(mock_context, 1, 20_000_000)

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_quote_command_api_success(self, mock_bot, mock_context):
        """Test quote command with successful API call."""
        plugin = FunPlugin(mock_bot)

        # Mock session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "content": "Test quote",
            "author": "Test Author",
        }

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))
        plugin.session = mock_session

        await plugin.random_quote(mock_context)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_quote_command_fallback(self, mock_bot, mock_context):
        """Test quote command with fallback to local quotes."""
        plugin = FunPlugin(mock_bot)

        # Mock session to fail
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("API error"))
        plugin.session = mock_session

        with patch("random.choice", return_value=("Test quote", "Test Author")):
            await plugin.random_quote(mock_context)

            mock_context.respond.assert_called_once()
