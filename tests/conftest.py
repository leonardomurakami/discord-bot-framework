"""Pytest configuration and shared fixtures."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import hikari
import lightbulb
import pytest

# Disable logging during tests
logging.disable(logging.CRITICAL)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_hikari_bot():
    """Mock Hikari bot instance."""
    bot = MagicMock(spec=hikari.GatewayBot)
    bot.cache = MagicMock()
    bot.rest = MagicMock()
    bot.get_me = MagicMock(
        return_value=MagicMock(
            id=12345,
            username="TestBot",
            display_name="TestBot",
            make_avatar_url=MagicMock(return_value="https://example.com/avatar.png"),
        )
    )
    bot.heartbeat_latency = 0.05

    # Mock cache methods
    bot.cache.get_guild = MagicMock(return_value=None)
    bot.cache.get_member = MagicMock(return_value=None)
    bot.cache.get_guild_channel = MagicMock(return_value=None)
    bot.cache.get_role = MagicMock(return_value=None)
    bot.cache.get_guilds_view = MagicMock(return_value={})
    bot.cache.get_members_view_for_guild = MagicMock(return_value={})
    bot.cache.get_guild_channels_view_for_guild = MagicMock(return_value={})
    bot.cache.get_roles_view_for_guild = MagicMock(return_value={})

    return bot


@pytest.fixture
def mock_lightbulb_client():
    """Mock Lightbulb client instance."""
    client = MagicMock(spec=lightbulb.Client)
    return client


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    db = AsyncMock()
    db.acquire = AsyncMock()
    db.health_check = AsyncMock(return_value=True)

    # Mock session context manager
    mock_session = AsyncMock()
    db.session = MagicMock(return_value=AsyncContextManager(mock_session))

    return db


@pytest.fixture
def mock_permission_manager():
    """Mock permission manager."""
    perm_manager = AsyncMock()
    perm_manager.has_permission = AsyncMock(return_value=True)
    perm_manager.get_role_permissions = AsyncMock(return_value=[])
    perm_manager.get_all_permissions = AsyncMock(return_value=[])
    perm_manager.grant_permission = AsyncMock(return_value=True)
    perm_manager.revoke_permission = AsyncMock(return_value=True)
    return perm_manager


@pytest.fixture
def mock_plugin_loader():
    """Mock plugin loader."""
    loader = MagicMock()
    loader.get_loaded_plugins = MagicMock(return_value=[])
    loader.get_plugin_info = MagicMock(return_value=None)
    loader.plugins = {}
    return loader


@pytest.fixture
def mock_event_system():
    """Mock event system."""
    event_system = MagicMock()
    return event_system


@pytest.fixture
def mock_bot(
    mock_hikari_bot,
    mock_lightbulb_client,
    mock_db_manager,
    mock_permission_manager,
    mock_plugin_loader,
    mock_event_system,
):
    """Mock complete bot instance."""
    bot = MagicMock()
    bot.hikari_bot = mock_hikari_bot
    bot.bot = mock_lightbulb_client
    bot.db = mock_db_manager
    bot.permission_manager = mock_permission_manager
    bot.plugin_loader = mock_plugin_loader
    bot.event_system = mock_event_system
    bot.miru_client = MagicMock()
    bot.get_guild_prefix = AsyncMock(return_value="!")
    return bot


@pytest.fixture
def mock_guild():
    """Mock Discord guild."""
    guild = MagicMock(spec=hikari.Guild)
    guild.id = 123456789
    guild.name = "Test Guild"
    guild.owner_id = 987654321
    guild.member_count = 100
    guild.created_at = MagicMock()
    guild.created_at.timestamp.return_value = 1640995200  # 2022-01-01
    guild.make_icon_url = MagicMock(return_value="https://example.com/icon.png")
    guild.make_banner_url = MagicMock(return_value="https://example.com/banner.png")
    guild.features = ["COMMUNITY", "NEWS"]
    guild.get_channels = MagicMock(return_value={})
    guild.get_roles = MagicMock(return_value={})
    guild.get_emojis = MagicMock(return_value={})
    guild.fetch_member = AsyncMock()
    guild.kick = AsyncMock()
    guild.ban = AsyncMock()
    guild.unban = AsyncMock()

    # Create proper async iterator for fetch_bans
    async def mock_fetch_bans():
        # Return empty by default
        return
        yield  # Make this a generator

    guild.fetch_bans = mock_fetch_bans
    return guild


@pytest.fixture
def mock_user():
    """Mock Discord user."""
    user = MagicMock(spec=hikari.User)
    user.id = 111111111
    user.username = "testuser"
    user.display_name = "Test User"
    user.is_bot = False
    user.created_at = MagicMock()
    user.created_at.timestamp.return_value = 1640995200
    user.make_avatar_url = MagicMock(return_value="https://example.com/avatar.png")
    user.display_avatar_url = "https://example.com/avatar.png"
    user.mention = "<@111111111>"
    return user


@pytest.fixture
def mock_member(mock_user):
    """Mock Discord member."""
    member = MagicMock(spec=hikari.Member)
    member.id = mock_user.id
    member.username = mock_user.username
    member.display_name = mock_user.display_name
    member.is_bot = mock_user.is_bot
    member.user = mock_user
    member.joined_at = MagicMock()
    member.joined_at.timestamp.return_value = 1641081600  # 2022-01-02
    member.role_ids = [222222222, 333333333]
    member.permissions = hikari.Permissions.SEND_MESSAGES | hikari.Permissions.READ_MESSAGE_HISTORY
    member.edit = AsyncMock()
    return member


@pytest.fixture
def mock_channel():
    """Mock Discord channel."""
    channel = MagicMock(spec=hikari.GuildTextChannel)
    channel.id = 444444444
    channel.name = "test-channel"
    channel.type = hikari.ChannelType.GUILD_TEXT
    channel.mention = "<#444444444>"
    channel.edit = AsyncMock()
    channel.delete_messages = AsyncMock()

    # Create proper async iterator for fetch_history
    async def mock_fetch_history(*args, **kwargs):
        mock_message = MagicMock()
        mock_message.id = 123
        mock_message.author = MagicMock()
        mock_message.author.id = 111111111
        for _ in range(5):  # Return 5 mock messages
            yield mock_message

    channel.fetch_history = mock_fetch_history
    return channel


@pytest.fixture
def mock_message_event(mock_user, mock_guild, mock_channel, mock_member):
    """Mock message create event."""
    event = MagicMock(spec=hikari.GuildMessageCreateEvent)
    event.author = mock_user
    event.member = mock_member
    event.guild_id = mock_guild.id
    event.channel_id = mock_channel.id
    event.content = "!test command"
    event.message = MagicMock()
    event.message.respond = AsyncMock()
    event.get_channel = MagicMock(return_value=mock_channel)
    return event


@pytest.fixture
def mock_context(mock_user, mock_guild, mock_channel, mock_member, mock_bot):
    """Mock command context."""
    ctx = MagicMock()
    ctx.author = mock_user
    ctx.member = mock_member
    ctx.guild_id = mock_guild.id
    ctx.channel_id = mock_channel.id
    ctx.bot = mock_bot
    ctx.get_guild = MagicMock(return_value=mock_guild)
    ctx.get_channel = MagicMock(return_value=mock_channel)
    ctx.respond = AsyncMock()
    ctx.defer = AsyncMock()
    ctx.edit_response = AsyncMock()
    return ctx


@pytest.fixture
def sample_plugin_metadata():
    """Sample plugin metadata for testing."""
    return {
        "name": "Test Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "A test plugin for unit testing",
        "permissions": ["test.command1", "test.command2"],
    }


class AsyncContextManager:
    """Helper for mocking async context managers."""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_context_manager():
    """Factory for creating async context managers."""
    return AsyncContextManager
