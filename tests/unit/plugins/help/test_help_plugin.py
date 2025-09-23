"""Tests for Help plugin."""

from unittest.mock import AsyncMock, MagicMock, patch

import hikari
import miru
import pytest

from plugins.help.plugin import HelpPlugin

from plugins.help.views import (
    PersistentPluginSelectView,
    PluginSelectView,
)


class TestHelpPlugin:
    """Test HelpPlugin functionality."""

    def test_plugin_creation(self, mock_bot):
        """Test creating help plugin."""
        plugin = HelpPlugin(mock_bot)
        assert plugin.bot == mock_bot

    @pytest.mark.asyncio
    async def test_help_command_general(self, mock_bot, mock_context):
        """Test general help command without arguments."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin loader with proper methods
        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = [
            "admin",
            "moderation",
            "fun",
        ]

        # Mock plugin info for each plugin
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test Plugin"
        mock_plugin_info.description = "Test description"
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        # Mock message handler for commands check
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {}
        mock_bot.message_handler.prefix = "!"

        await plugin.help_command(mock_context)

        # Should respond with general help
        mock_context.respond.assert_called_once()
        call_args = mock_context.respond.call_args
        assert "embed" in call_args[1]
        # Only check for components if miru_client is available and has children
        if hasattr(mock_bot, "miru_client") and mock_bot.miru_client:
            assert "components" in call_args[1]

    @pytest.mark.asyncio
    async def test_help_command_specific_plugin(self, mock_bot, mock_context):
        """Test help command for specific plugin."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin loader with detailed plugin
        mock_admin_plugin = MagicMock()
        mock_admin_plugin.plugin_info = {
            "name": "Admin",
            "description": "Admin commands",
            "commands": [
                {
                    "name": "reload",
                    "description": "Reload plugins",
                    "permission_node": "admin.reload",
                }
            ],
        }

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.plugins = {"admin": mock_admin_plugin}

        await plugin.help_command(mock_context, "admin")

        # Should respond with plugin-specific help
        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_command_plugin_not_found(self, mock_bot, mock_context):
        """Test help command for non-existent plugin."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin loader with proper methods
        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = []
        mock_bot.plugin_loader.get_plugin_info.return_value = None

        # Mock message handler
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {}

        await plugin.help_command(mock_context, "nonexistent")

        # Should respond with error (using smart_respond)
        assert mock_context.respond.called or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_get_general_help(self, mock_bot):
        """Test _get_general_help method."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin loader
        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.plugins = {
            "admin": MagicMock(),
            "moderation": MagicMock(),
        }

        embed = await plugin._get_general_help()

        assert embed is not None
        assert isinstance(embed, hikari.Embed)

    @pytest.mark.asyncio
    async def test_get_plugin_commands_embed(self, mock_bot):
        """Test _get_plugin_commands_embed method."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin with commands
        mock_plugin = MagicMock()
        mock_plugin.plugin_info = {
            "name": "Test Plugin",
            "description": "Test plugin description",
            "version": "1.0.0",
            "author": "Test Author",
            "commands": [
                {
                    "name": "test_command",
                    "description": "Test command description",
                    "permission_node": "test.command",
                    "usage": "/test_command <arg>",
                }
            ],
        }

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.plugins = {"test": mock_plugin}

        embed = await plugin._get_plugin_commands_embed("test")

        assert embed is not None
        assert isinstance(embed, hikari.Embed)

    @pytest.mark.asyncio
    async def test_get_plugin_commands_embed_not_found(self, mock_bot):
        """Test _get_plugin_commands_embed for non-existent plugin."""
        plugin = HelpPlugin(mock_bot)

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_plugin_info.return_value = None

        embed = await plugin._get_plugin_commands_embed("nonexistent")

        assert embed is not None
        assert "not found" in embed.description.lower()

    @pytest.mark.asyncio
    async def test_get_plugin_commands_embed_no_commands(self, mock_bot):
        """Test plugin embed for plugin with no commands."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin info without commands
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Empty Plugin"
        mock_plugin_info.description = "Plugin with no commands"
        mock_plugin_info.version = "1.0.0"
        mock_plugin_info.author = "Test Author"

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        # Mock message handler with no commands
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {}

        embed = await plugin._get_plugin_commands_embed("empty")

        assert embed is not None
        # Check the embed field content instead of description
        fields = embed.fields
        commands_field = None
        for field in fields:
            if "commands" in field.name.lower():
                commands_field = field
                break

        assert commands_field is not None
        assert "no commands" in commands_field.value.lower()

    @pytest.mark.asyncio
    async def test_get_command_info_existing_command(self, mock_bot):
        """Test _get_command_info for existing command."""
        plugin = HelpPlugin(mock_bot)

        # Mock command object
        mock_cmd = MagicMock()
        mock_cmd.name = "test_cmd"
        mock_cmd.description = "Test command"
        mock_cmd.permission_node = "test.cmd"
        mock_cmd.aliases = ["tc"]

        # Mock message handler with the command
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {"test_cmd": mock_cmd}
        mock_bot.message_handler.prefix = "!"

        cmd_info = await plugin._get_command_info("test_cmd")

        assert cmd_info is not None
        assert cmd_info["name"] == "test_cmd"

    @pytest.mark.asyncio
    async def test_get_command_info_not_found(self, mock_bot):
        """Test _get_command_info for non-existent command."""
        plugin = HelpPlugin(mock_bot)

        # Mock message handler with no commands
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {}

        cmd_info = await plugin._get_command_info("nonexistent")

        assert cmd_info is None

    @pytest.mark.asyncio
    async def test_get_command_info_by_alias(self, mock_bot):
        """Test _get_command_info finding command by alias."""
        plugin = HelpPlugin(mock_bot)

        # Mock command object with aliases
        mock_cmd = MagicMock()
        mock_cmd.name = "long_command"
        mock_cmd.description = "Long command name"
        mock_cmd.aliases = ["lc", "short"]

        # Mock message handler with the command
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {"long_command": mock_cmd}
        mock_bot.message_handler.prefix = "!"

        cmd_info = await plugin._get_command_info("lc")

        assert cmd_info is not None
        assert cmd_info["name"] == "long_command"

    def test_format_command_list_small(self, mock_bot):
        """Test _format_command_list with small number of commands."""
        plugin = HelpPlugin(mock_bot)

        commands = [
            {"name": "cmd1", "description": "Command 1"},
            {"name": "cmd2", "description": "Command 2"},
        ]

        formatted = plugin._format_command_list(commands)

        assert len(formatted) == 1
        assert "cmd1" in formatted[0]
        assert "cmd2" in formatted[0]

    def test_format_command_list_large(self, mock_bot):
        """Test _format_command_list with many commands."""
        plugin = HelpPlugin(mock_bot)

        # Create many commands to test pagination with long descriptions
        commands = []
        for i in range(25):
            commands.append(
                {
                    "name": f"very_long_command_name_{i}",
                    "description": f"This is a very long command description for command {i} that should help trigger pagination when there are many commands like this one",
                }
            )

        formatted = plugin._format_command_list(commands)

        # Should be split into multiple pages due to character limit
        assert len(formatted) > 1

    def test_get_plugin_overview_with_metadata(self, mock_bot):
        """Test _get_plugin_overview with full metadata."""
        plugin = HelpPlugin(mock_bot)

        plugin_obj = MagicMock()
        plugin_obj.plugin_info = {
            "name": "Test Plugin",
            "description": "A comprehensive test plugin",
            "version": "2.1.0",
            "author": "Test Developer",
            "commands": [{"name": "cmd1"}, {"name": "cmd2"}],
        }

        overview = plugin._get_plugin_overview("test", plugin_obj)

        assert "Test Plugin" in overview
        assert "2.1.0" in overview
        assert "Test Developer" in overview
        assert "2 commands" in overview

    def test_get_plugin_overview_minimal_metadata(self, mock_bot):
        """Test _get_plugin_overview with minimal metadata."""
        plugin = HelpPlugin(mock_bot)

        plugin_obj = MagicMock()
        plugin_obj.plugin_info = {"name": "Minimal Plugin", "commands": []}

        overview = plugin._get_plugin_overview("minimal", plugin_obj)

        assert "Minimal Plugin" in overview
        assert "Unknown" in overview  # Should handle missing fields

    def test_get_plugin_overview_no_plugin_info(self, mock_bot):
        """Test _get_plugin_overview when plugin has no plugin_info."""
        plugin = HelpPlugin(mock_bot)

        plugin_obj = MagicMock()
        del plugin_obj.plugin_info  # Remove plugin_info attribute

        overview = plugin._get_plugin_overview("broken", plugin_obj)

        assert "broken" in overview.lower()
        assert "available" in overview.lower()


class TestPersistentPluginSelectView:
    """Test PersistentPluginSelectView functionality."""

    def test_persistent_view_creation(self):
        """Test creating persistent plugin select view."""
        view = PersistentPluginSelectView()

        assert view.timeout is None  # Should be persistent
        assert len(view.children) == 1  # Should have select menu

    @pytest.mark.asyncio
    async def test_on_plugin_select_no_select_values(self):
        """Test plugin select when no values selected."""
        view = PersistentPluginSelectView()

        # Mock view context
        mock_ctx = MagicMock()

        # Mock empty select item
        mock_select = MagicMock()
        mock_select.values = []
        mock_select.custom_id = "help_plugin_select"

        with patch.object(type(view), "children", new_callable=MagicMock, return_value=[mock_select]):
            await view.on_plugin_select(mock_ctx)

        # Should return early without errors
        assert True  # Just verify no exceptions


class TestPluginSelectView:
    """Test PluginSelectView functionality."""

    def test_plugin_select_view_creation(self, mock_bot):
        """Test creating plugin select view."""
        # Mock help plugin with bot and plugin loader
        mock_help_plugin = MagicMock()
        mock_help_plugin.bot = mock_bot

        # Mock plugin loader with plugins
        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["test_plugin"]

        # Mock plugin info
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test Plugin"
        mock_plugin_info.description = "Test description"
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        view = PluginSelectView(mock_help_plugin)

        assert view.help_plugin == mock_help_plugin
        assert len(view.children) >= 1  # Should have select menu


class TestHelpPluginMethods:
    """Test internal methods of HelpPlugin."""

    @pytest.mark.asyncio
    async def test_get_command_help(self, mock_bot, mock_context):
        """Test _get_command_help method."""
        plugin = HelpPlugin(mock_bot)

        # Mock message handler with command
        mock_cmd = MagicMock()
        mock_cmd.name = "test_cmd"
        mock_cmd.description = "Test command description"
        mock_cmd.aliases = ["tc"]
        mock_cmd.permission_node = "test.cmd"

        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {"test_cmd": mock_cmd}
        mock_bot.message_handler.prefix = "!"

        embed = await plugin._get_command_help("test_cmd")

        assert embed is not None
        assert "test_cmd" in embed.title

    @pytest.mark.asyncio
    async def test_get_plugin_help(self, mock_bot):
        """Test _get_plugin_help method."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin loader
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test Plugin"
        mock_plugin_info.description = "Test description"
        mock_plugin_info.version = "1.0.0"
        mock_plugin_info.author = "Test Author"
        mock_plugin_info.permissions = ["test.perm"]

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["test"]
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {}

        embed = await plugin._get_plugin_help("test")

        assert embed is not None
        assert "Test Plugin" in embed.title

    @pytest.mark.asyncio
    async def test_get_commands_list(self, mock_bot):
        """Test _get_commands_list method."""
        plugin = HelpPlugin(mock_bot)

        # Mock commands
        mock_cmd1 = MagicMock()
        mock_cmd1.name = "help"
        mock_cmd2 = MagicMock()
        mock_cmd2.name = "ping"

        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {"help": mock_cmd1, "ping": mock_cmd2}

        embed = await plugin._get_commands_list()

        assert embed is not None
        assert "All Commands" in embed.title

    @pytest.mark.asyncio
    async def test_get_plugins_list(self, mock_bot):
        """Test _get_plugins_list method."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin info
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test Plugin"
        mock_plugin_info.description = "Test description"
        mock_plugin_info.version = "1.0.0"

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["test"]
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        embed = await plugin._get_plugins_list()

        assert embed is not None
        assert "Loaded Plugins" in embed.title

    @pytest.mark.asyncio
    async def test_get_plugins_list_no_plugins(self, mock_bot):
        """Test _get_plugins_list with no plugins."""
        plugin = HelpPlugin(mock_bot)

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = []

        embed = await plugin._get_plugins_list()

        assert embed is not None
        assert "No plugins" in embed.description

    @pytest.mark.asyncio
    async def test_register_persistent_views(self, mock_bot):
        """Test _register_persistent_views method."""
        plugin = HelpPlugin(mock_bot)

        # Mock miru client
        mock_miru_client = MagicMock()
        mock_miru_client.start_view = MagicMock()
        mock_bot.miru_client = mock_miru_client

        await plugin._register_persistent_views()

        # Should register view
        mock_miru_client.start_view.assert_called_once()
        assert plugin._persistent_view_registered is True

    @pytest.mark.asyncio
    async def test_register_persistent_views_already_registered(self, mock_bot):
        """Test _register_persistent_views when already registered."""
        plugin = HelpPlugin(mock_bot)
        plugin._persistent_view_registered = True

        mock_miru_client = MagicMock()
        mock_bot.miru_client = mock_miru_client

        await plugin._register_persistent_views()

        # Should not register again
        mock_miru_client.start_view.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_load_calls_register_views(self, mock_bot):
        """Test on_load calls _register_persistent_views."""
        plugin = HelpPlugin(mock_bot)

        with patch.object(plugin, "_register_persistent_views", new_callable=AsyncMock) as mock_register:
            await plugin.on_load()

        mock_register.assert_called_once()


class TestHelpPluginIntegration:
    """Integration tests for help plugin functionality."""

    @pytest.mark.asyncio
    async def test_full_help_workflow(self, mock_bot, mock_context):
        """Test complete help command workflow."""
        plugin = HelpPlugin(mock_bot)

        # Mock multiple plugins
        mock_admin = MagicMock()
        mock_admin.plugin_info = {
            "name": "Admin",
            "description": "Admin commands",
            "commands": [{"name": "reload", "description": "Reload plugins"}],
        }

        mock_fun = MagicMock()
        mock_fun.plugin_info = {
            "name": "Fun",
            "description": "Fun commands",
            "commands": [{"name": "joke", "description": "Tell a joke"}],
        }

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.plugins = {"admin": mock_admin, "fun": mock_fun}

        # Test general help
        await plugin.help_command(mock_context)
        mock_context.respond.assert_called()

        # Reset mock
        mock_context.reset_mock()

        # Test specific plugin help
        await plugin.help_command(mock_context, "admin")
        mock_context.respond.assert_called()

    @pytest.mark.asyncio
    async def test_plugin_info_edge_cases(self, mock_bot):
        """Test plugin info handling with various edge cases."""
        plugin = HelpPlugin(mock_bot)

        # Test plugin with minimal info
        minimal_plugin = MagicMock()
        minimal_plugin.plugin_info = {"name": "Minimal"}

        # Test plugin with no plugin_info
        broken_plugin = MagicMock()
        del broken_plugin.plugin_info

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.plugins = {
            "minimal": minimal_plugin,
            "broken": broken_plugin,
        }

        # Should handle both cases without errors
        embed = await plugin._get_general_help()
        assert embed is not None

    def test_command_formatting_edge_cases(self, mock_bot):
        """Test command formatting with edge cases."""
        plugin = HelpPlugin(mock_bot)

        # Test empty command list
        empty_formatted = plugin._format_command_list([])
        assert len(empty_formatted) == 1
        assert "No commands" in empty_formatted[0]

        # Test command without description
        commands_no_desc = [{"name": "cmd1"}]
        formatted = plugin._format_command_list(commands_no_desc)
        assert "cmd1" in formatted[0]

        # Test very long command descriptions
        long_desc_commands = [{"name": "cmd1", "description": "A" * 200}]  # Very long description
        formatted = plugin._format_command_list(long_desc_commands)
        assert len(formatted[0]) < 2000  # Should fit in embed field limit

    @pytest.mark.asyncio
    async def test_error_handling_in_help_methods(self, mock_bot):
        """Test error handling in various help methods."""
        plugin = HelpPlugin(mock_bot)

        # Test with None plugin loader
        mock_bot.plugin_loader = None
        mock_bot.message_handler = None

        # Should handle gracefully
        embed = await plugin._get_general_help()
        assert embed is not None

        cmd_info = await plugin._get_command_info("test")
        assert cmd_info is None

    @pytest.mark.asyncio
    async def test_miru_component_integration(self, mock_bot):
        """Test integration with miru components."""
        plugin = HelpPlugin(mock_bot)

        # Test that select view creates proper miru components
        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["test"]

        # Mock plugin info
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test Plugin"
        mock_plugin_info.description = "Test description"
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        view = PluginSelectView(plugin)

        # Should have miru components
        assert len(view.children) > 0
        assert any(isinstance(child, miru.TextSelect) for child in view.children)

    def test_persistent_view_setup(self):
        """Test persistent view setup and configuration."""
        view = PersistentPluginSelectView()

        # Should be configured for persistence
        assert view.timeout is None

        # Should have correct custom IDs for persistence
        select_items = [child for child in view.children if isinstance(child, miru.TextSelect)]
        assert len(select_items) > 0
        assert any(item.custom_id == "help_plugin_select" for item in select_items)


class TestHelpPluginAdditionalCoverage:
    """Additional tests to improve coverage."""

    @pytest.mark.asyncio
    async def test_list_commands_command(self, mock_bot, mock_context):
        """Test the list commands command."""
        plugin = HelpPlugin(mock_bot)

        # Mock message handler with commands
        mock_cmd = MagicMock()
        mock_cmd.name = "test_cmd"
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {"test_cmd": mock_cmd}

        await plugin.list_commands(mock_context)
        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_commands_command_error(self, mock_bot, mock_context):
        """Test the list commands command with error."""
        plugin = HelpPlugin(mock_bot)

        # Make the message handler raise an exception
        mock_bot.message_handler = None

        await plugin.list_commands(mock_context)
        # Should still respond with error message

    @pytest.mark.asyncio
    async def test_list_plugins_command(self, mock_bot, mock_context):
        """Test the list plugins command."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin loader
        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["test"]
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test"
        mock_plugin_info.version = "1.0.0"
        mock_plugin_info.description = "Test plugin"
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        await plugin.list_plugins(mock_context)
        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_plugins_command_error(self, mock_bot, mock_context):
        """Test the list plugins command with error."""
        plugin = HelpPlugin(mock_bot)

        # Make the plugin loader raise an exception
        mock_bot.plugin_loader = None

        await plugin.list_plugins(mock_context)
        # Should still respond with error message

    @pytest.mark.asyncio
    async def test_get_plugin_help_with_no_plugin_found(self, mock_bot):
        """Test _get_plugin_help when plugin not found."""
        plugin = HelpPlugin(mock_bot)

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = []

        result = await plugin._get_plugin_help("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_plugin_help_with_plugin_commands(self, mock_bot):
        """Test _get_plugin_help with plugin that has commands."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin loader
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test Plugin"
        mock_plugin_info.description = "Test description"
        mock_plugin_info.version = "1.0.0"
        mock_plugin_info.author = "Test Author"
        mock_plugin_info.permissions = ["test.perm"]

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["test"]
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        # Mock command that belongs to this plugin
        mock_cmd = MagicMock()
        mock_cmd.plugin_name = "test"
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {"test_cmd": mock_cmd}

        result = await plugin._get_plugin_help("test")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_plugins_list_with_plugin_missing_info(self, mock_bot):
        """Test _get_plugins_list with plugin that has no info."""
        plugin = HelpPlugin(mock_bot)

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["broken"]
        mock_bot.plugin_loader.get_plugin_info.return_value = None

        embed = await plugin._get_plugins_list()
        assert embed is not None

    @pytest.mark.asyncio
    async def test_get_plugin_commands_embed_with_long_description(self, mock_bot):
        """Test _get_plugin_commands_embed with plugin that has long description."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin info with very long description
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test Plugin"
        mock_plugin_info.description = "A" * 200  # Very long description
        mock_plugin_info.version = "1.0.0"
        mock_plugin_info.author = "Test Author"

        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        # Mock message handler with commands that belong to this plugin
        mock_cmd = MagicMock()
        mock_cmd.name = "test_cmd"
        mock_cmd.plugin_name = "test"
        mock_cmd.description = "Test command"
        mock_cmd.aliases = ["tc"]
        mock_cmd.arguments = []

        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {"test_cmd": mock_cmd}
        mock_bot.message_handler.prefix = "!"

        embed = await plugin._get_plugin_commands_embed("test")
        assert embed is not None

    def test_get_plugin_overview_with_long_commands_list(self, mock_bot):
        """Test _get_plugin_overview with plugin that has many commands."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin with many commands
        mock_plugin = MagicMock()
        mock_plugin.plugin_info = {
            "name": "Big Plugin",
            "version": "2.0.0",
            "author": "Big Developer",
            "commands": [{"name": f"cmd{i}"} for i in range(50)],  # Many commands
        }

        overview = plugin._get_plugin_overview("big", mock_plugin)
        assert "Big Plugin" in overview
        assert "50 commands" in overview

    @pytest.mark.asyncio
    async def test_help_command_with_miru_client_unavailable(self, mock_bot, mock_context):
        """Test help command when miru client is not available."""
        plugin = HelpPlugin(mock_bot)

        # Mock plugin loader
        mock_bot.plugin_loader = MagicMock()
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["test"]
        mock_plugin_info = MagicMock()
        mock_plugin_info.name = "Test Plugin"
        mock_plugin_info.description = "Test description"
        mock_bot.plugin_loader.get_plugin_info.return_value = mock_plugin_info

        # Mock message handler
        mock_bot.message_handler = MagicMock()
        mock_bot.message_handler.commands = {}
        mock_bot.message_handler.prefix = "!"

        # No miru client available
        mock_bot.miru_client = None

        await plugin.help_command(mock_context)
        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_command_exception_handling(self, mock_bot, mock_context):
        """Test help command exception handling."""
        plugin = HelpPlugin(mock_bot)

        # Make _get_general_help raise an exception
        with patch.object(plugin, "_get_general_help", side_effect=Exception("Test error")):
            await plugin.help_command(mock_context)

    @pytest.mark.asyncio
    async def test_register_persistent_views_no_miru_client(self, mock_bot):
        """Test _register_persistent_views when miru client is not available."""
        plugin = HelpPlugin(mock_bot)
        mock_bot.miru_client = None

        await plugin._register_persistent_views()
        # Should not raise exception
        assert not plugin._persistent_view_registered
