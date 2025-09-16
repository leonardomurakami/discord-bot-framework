import os
import sys
import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Type, Optional, Any
import logging

from ..plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class PluginMetadata:
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        author: str = "Unknown",
        description: str = "",
        dependencies: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.dependencies = dependencies or []
        self.permissions = permissions or []


class PluginLoader:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.plugin_directories: List[Path] = []
        pass

    def add_plugin_directory(self, directory: str) -> None:
        path = Path(directory)
        if path.exists() and path.is_dir():
            self.plugin_directories.append(path)
            logger.info(f"Added plugin directory: {path}")
        else:
            logger.warning(f"Plugin directory does not exist: {path}")

    def discover_plugins(self) -> List[str]:
        discovered = []

        for directory in self.plugin_directories:
            for plugin_path in directory.iterdir():
                if plugin_path.is_dir() and not plugin_path.name.startswith("_"):
                    init_file = plugin_path / "__init__.py"
                    if init_file.exists():
                        discovered.append(plugin_path.name)

        logger.info(f"Discovered plugins: {discovered}")
        return discovered

    def _load_plugin_module(self, plugin_name: str) -> Any:
        for directory in self.plugin_directories:
            plugin_path = directory / plugin_name
            if plugin_path.exists():
                spec = importlib.util.spec_from_file_location(
                    f"plugins.{plugin_name}",
                    plugin_path / "__init__.py"
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"plugins.{plugin_name}"] = module
                    spec.loader.exec_module(module)
                    return module

        raise ImportError(f"Plugin {plugin_name} not found")

    def _extract_plugin_class(self, module: Any) -> Type[BasePlugin]:
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BasePlugin) and
                obj is not BasePlugin and
                hasattr(obj, "__module__") and
                module.__name__ in obj.__module__
            ):
                return obj

        # If we can't find a plugin class, look for setup function
        if hasattr(module, 'setup'):
            return module.setup

        raise ValueError(f"No plugin class found in module {module.__name__}")

    def _extract_metadata(self, module: Any) -> PluginMetadata:
        if hasattr(module, "PLUGIN_METADATA"):
            meta_dict = module.PLUGIN_METADATA
            return PluginMetadata(
                name=meta_dict.get("name", "Unknown"),
                version=meta_dict.get("version", "1.0.0"),
                author=meta_dict.get("author", "Unknown"),
                description=meta_dict.get("description", ""),
                dependencies=meta_dict.get("dependencies", []),
                permissions=meta_dict.get("permissions", []),
            )
        else:
            return PluginMetadata(name=module.__name__)

    async def load_plugin(self, plugin_name: str) -> bool:
        try:
            # Check if plugin is already loaded
            if plugin_name in self.plugins:
                logger.info(f"Plugin {plugin_name} is already loaded")
                return True

            # Load the module
            module = self._load_plugin_module(plugin_name)

            # Extract metadata
            metadata = self._extract_metadata(module)

            # Check dependencies
            for dep in metadata.dependencies:
                if dep not in self.plugins:
                    logger.error(f"Plugin {plugin_name} requires {dep} which is not loaded")
                    return False

            # Extract and instantiate plugin class
            plugin_class_or_setup = self._extract_plugin_class(module)

            # If it's a setup function, call it to get the plugin instance
            if callable(plugin_class_or_setup) and hasattr(module, 'setup'):
                plugin_instance = plugin_class_or_setup(self.bot)
            else:
                # Otherwise, instantiate the class
                plugin_instance = plugin_class_or_setup(self.bot)

            # Initialize plugin
            await plugin_instance.on_load()

            # Store plugin and metadata
            self.plugins[plugin_name] = plugin_instance
            self.plugin_metadata[plugin_name] = metadata

            logger.info(f"Successfully loaded plugin: {plugin_name} v{metadata.version}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return False

    async def unload_plugin(self, plugin_name: str) -> bool:
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} is not loaded")
                return False

            plugin = self.plugins[plugin_name]

            # Call plugin cleanup
            await plugin.on_unload()

            # Remove from loaded plugins
            del self.plugins[plugin_name]
            del self.plugin_metadata[plugin_name]

            # Remove from sys.modules to allow reloading
            module_name = f"plugins.{plugin_name}"
            if module_name in sys.modules:
                del sys.modules[module_name]

            logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False

    async def reload_plugin(self, plugin_name: str) -> bool:
        if await self.unload_plugin(plugin_name):
            return await self.load_plugin(plugin_name)
        return False

    async def load_all_plugins(self, enabled_plugins: List[str]) -> None:
        for plugin_name in enabled_plugins:
            await self.load_plugin(plugin_name)

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        return self.plugins.get(plugin_name)

    def get_loaded_plugins(self) -> List[str]:
        return list(self.plugins.keys())

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginMetadata]:
        return self.plugin_metadata.get(plugin_name)