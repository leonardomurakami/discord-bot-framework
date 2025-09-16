"""Tests for plugin loader functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.core.plugin_loader import PluginLoader, PluginMetadata
from bot.plugins.base import BasePlugin


class TestPluginMetadata:
    """Test PluginMetadata class."""

    def test_metadata_creation(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="Test Plugin",
            version="1.0.0",
            author="Test Author",
            description="Test description",
            dependencies=["dep1", "dep2"],
            permissions=["perm1", "perm2"],
        )

        assert metadata.name == "Test Plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test description"
        assert metadata.dependencies == ["dep1", "dep2"]
        assert metadata.permissions == ["perm1", "perm2"]

    def test_metadata_defaults(self):
        """Test metadata with default values."""
        metadata = PluginMetadata(name="Test")

        assert metadata.name == "Test"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Unknown"
        assert metadata.description == ""
        assert metadata.dependencies == []
        assert metadata.permissions == []


class TestPluginLoader:
    """Test PluginLoader class."""

    def test_loader_creation(self, mock_bot):
        """Test creating a plugin loader."""
        loader = PluginLoader(mock_bot)

        assert loader.bot == mock_bot
        assert loader.plugins == {}
        assert loader.plugin_metadata == {}
        assert loader.plugin_directories == []

    def test_add_plugin_directory(self, mock_bot, tmp_path):
        """Test adding a plugin directory."""
        loader = PluginLoader(mock_bot)
        test_dir = tmp_path / "plugins"
        test_dir.mkdir()

        loader.add_plugin_directory(str(test_dir))

        assert test_dir in loader.plugin_directories

    def test_add_nonexistent_directory(self, mock_bot):
        """Test adding a non-existent directory."""
        loader = PluginLoader(mock_bot)

        loader.add_plugin_directory("/nonexistent/path")

        assert len(loader.plugin_directories) == 0

    def test_discover_plugins(self, mock_bot, tmp_path):
        """Test discovering plugins."""
        loader = PluginLoader(mock_bot)

        # Create mock plugin directories
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        plugin1_dir = plugin_dir / "plugin1"
        plugin1_dir.mkdir()
        (plugin1_dir / "__init__.py").touch()

        plugin2_dir = plugin_dir / "plugin2"
        plugin2_dir.mkdir()
        (plugin2_dir / "__init__.py").touch()

        loader.add_plugin_directory(str(plugin_dir))

        discovered = loader.discover_plugins()

        assert "plugin1" in discovered
        assert "plugin2" in discovered

    def test_extract_metadata_with_module_metadata(self, mock_bot):
        """Test extracting metadata from module with PLUGIN_METADATA."""
        loader = PluginLoader(mock_bot)

        mock_module = MagicMock()
        mock_module.PLUGIN_METADATA = {
            "name": "Test Plugin",
            "version": "2.0.0",
            "author": "Test Author",
            "description": "Test description",
            "dependencies": ["dep1"],
            "permissions": ["perm1"],
        }

        metadata = loader._extract_metadata(mock_module)

        assert metadata.name == "Test Plugin"
        assert metadata.version == "2.0.0"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test description"
        assert metadata.dependencies == ["dep1"]
        assert metadata.permissions == ["perm1"]

    def test_extract_metadata_without_module_metadata(self, mock_bot):
        """Test extracting metadata from module without PLUGIN_METADATA."""
        loader = PluginLoader(mock_bot)

        mock_module = MagicMock()
        mock_module.__name__ = "test_plugin"
        del mock_module.PLUGIN_METADATA  # Ensure it doesn't exist

        metadata = loader._extract_metadata(mock_module)

        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Unknown"

    def test_extract_plugin_class(self, mock_bot):
        """Test extracting plugin class from module."""
        loader = PluginLoader(mock_bot)

        class TestPlugin(BasePlugin):
            pass

        mock_module = MagicMock()
        mock_module.__name__ = "test_plugin"

        with patch("inspect.getmembers") as mock_getmembers:
            mock_getmembers.return_value = [
                ("TestPlugin", TestPlugin),
                ("SomeOtherClass", str),
            ]

            result = loader._extract_plugin_class(mock_module)

            assert result == TestPlugin

    def test_extract_plugin_class_with_setup(self, mock_bot):
        """Test extracting plugin with setup function."""
        loader = PluginLoader(mock_bot)

        mock_module = MagicMock()
        mock_module.__name__ = "test_plugin"
        mock_module.setup = MagicMock()

        with patch("inspect.getmembers") as mock_getmembers:
            mock_getmembers.return_value = []

            result = loader._extract_plugin_class(mock_module)

            assert result == mock_module.setup

    def test_extract_plugin_class_not_found(self, mock_bot):
        """Test extracting plugin class when none found."""
        loader = PluginLoader(mock_bot)

        mock_module = MagicMock()
        mock_module.__name__ = "test_plugin"
        del mock_module.setup  # Ensure setup doesn't exist

        with patch("inspect.getmembers") as mock_getmembers:
            mock_getmembers.return_value = []

            with pytest.raises(ValueError):
                loader._extract_plugin_class(mock_module)

    @pytest.mark.asyncio
    async def test_load_plugin_success(self, mock_bot):
        """Test successful plugin loading."""
        loader = PluginLoader(mock_bot)

        class TestPlugin(BasePlugin):
            def __init__(self, bot):
                self.bot = bot

            async def on_load(self):
                pass

        mock_module = MagicMock()
        mock_module.PLUGIN_METADATA = {
            "name": "Test Plugin",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "Test description",
        }

        with (
            patch.object(loader, "_load_plugin_module", return_value=mock_module),
            patch.object(loader, "_extract_plugin_class", return_value=TestPlugin),
        ):

            result = await loader.load_plugin("test_plugin")

            assert result is True
            assert "test_plugin" in loader.plugins
            assert "test_plugin" in loader.plugin_metadata
            assert isinstance(loader.plugins["test_plugin"], TestPlugin)

    @pytest.mark.asyncio
    async def test_load_plugin_already_loaded(self, mock_bot):
        """Test loading a plugin that's already loaded."""
        loader = PluginLoader(mock_bot)

        # Mock an already loaded plugin
        mock_plugin = MagicMock()
        loader.plugins["test_plugin"] = mock_plugin

        result = await loader.load_plugin("test_plugin")

        assert result is True

    @pytest.mark.asyncio
    async def test_load_plugin_missing_dependency(self, mock_bot):
        """Test loading a plugin with missing dependency."""
        loader = PluginLoader(mock_bot)

        mock_module = MagicMock()
        mock_module.PLUGIN_METADATA = {
            "name": "Test Plugin",
            "dependencies": ["missing_plugin"],
        }

        with patch.object(loader, "_load_plugin_module", return_value=mock_module):
            result = await loader.load_plugin("test_plugin")

            assert result is False

    @pytest.mark.asyncio
    async def test_load_plugin_error(self, mock_bot):
        """Test loading a plugin with error."""
        loader = PluginLoader(mock_bot)

        with patch.object(
            loader, "_load_plugin_module", side_effect=Exception("Test error")
        ):
            result = await loader.load_plugin("test_plugin")

            assert result is False

    @pytest.mark.asyncio
    async def test_unload_plugin_success(self, mock_bot):
        """Test successful plugin unloading."""
        loader = PluginLoader(mock_bot)

        mock_plugin = AsyncMock()
        loader.plugins["test_plugin"] = mock_plugin
        loader.plugin_metadata["test_plugin"] = MagicMock()

        result = await loader.unload_plugin("test_plugin")

        assert result is True
        assert "test_plugin" not in loader.plugins
        assert "test_plugin" not in loader.plugin_metadata
        mock_plugin.on_unload.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_plugin_not_loaded(self, mock_bot):
        """Test unloading a plugin that's not loaded."""
        loader = PluginLoader(mock_bot)

        result = await loader.unload_plugin("nonexistent_plugin")

        assert result is False

    @pytest.mark.asyncio
    async def test_unload_plugin_error(self, mock_bot):
        """Test unloading a plugin with error."""
        loader = PluginLoader(mock_bot)

        mock_plugin = AsyncMock()
        mock_plugin.on_unload.side_effect = Exception("Test error")
        loader.plugins["test_plugin"] = mock_plugin

        result = await loader.unload_plugin("test_plugin")

        assert result is False

    @pytest.mark.asyncio
    async def test_reload_plugin_success(self, mock_bot):
        """Test successful plugin reloading."""
        loader = PluginLoader(mock_bot)

        with (
            patch.object(loader, "unload_plugin", return_value=True) as mock_unload,
            patch.object(loader, "load_plugin", return_value=True) as mock_load,
        ):

            result = await loader.reload_plugin("test_plugin")

            assert result is True
            mock_unload.assert_called_once_with("test_plugin")
            mock_load.assert_called_once_with("test_plugin")

    @pytest.mark.asyncio
    async def test_reload_plugin_unload_fail(self, mock_bot):
        """Test reloading a plugin when unload fails."""
        loader = PluginLoader(mock_bot)

        with patch.object(loader, "unload_plugin", return_value=False):
            result = await loader.reload_plugin("test_plugin")

            assert result is False

    @pytest.mark.asyncio
    async def test_reload_plugin_load_fail(self, mock_bot):
        """Test reloading a plugin when load fails."""
        loader = PluginLoader(mock_bot)

        with (
            patch.object(loader, "unload_plugin", return_value=True),
            patch.object(loader, "load_plugin", return_value=False),
        ):

            result = await loader.reload_plugin("test_plugin")

            assert result is False

    def test_get_loaded_plugins(self, mock_bot):
        """Test getting loaded plugins."""
        loader = PluginLoader(mock_bot)

        loader.plugins["plugin1"] = MagicMock()
        loader.plugins["plugin2"] = MagicMock()

        result = loader.get_loaded_plugins()

        assert "plugin1" in result
        assert "plugin2" in result

    def test_get_plugin_info(self, mock_bot):
        """Test getting plugin info."""
        loader = PluginLoader(mock_bot)

        metadata = PluginMetadata(name="Test Plugin")
        loader.plugin_metadata["test_plugin"] = metadata

        result = loader.get_plugin_info("test_plugin")

        assert result == metadata

    def test_get_plugin_info_not_found(self, mock_bot):
        """Test getting plugin info for non-existent plugin."""
        loader = PluginLoader(mock_bot)

        result = loader.get_plugin_info("nonexistent_plugin")

        assert result is None
