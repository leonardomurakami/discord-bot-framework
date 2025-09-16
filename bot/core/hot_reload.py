import asyncio
import logging
from pathlib import Path
from typing import Set, Dict, Any
from watchfiles import awatch, Change
import importlib
import sys

logger = logging.getLogger(__name__)


class HotReloadManager:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.watched_directories: Set[Path] = set()
        self.watch_task: asyncio.Task = None
        self.file_timestamps: Dict[str, float] = {}

    def add_watch_directory(self, directory: str | Path) -> None:
        path = Path(directory)
        if path.exists() and path.is_dir():
            self.watched_directories.add(path)
            logger.info(f"Added hot reload watch: {path}")
        else:
            logger.warning(f"Watch directory does not exist: {path}")

    def start_watching(self) -> None:
        if self.watch_task and not self.watch_task.done():
            logger.warning("Hot reload is already running")
            return

        if not self.watched_directories:
            logger.warning("No directories to watch for hot reload")
            return

        # Schedule the task to start when the event loop is running
        try:
            loop = asyncio.get_running_loop()
            self.watch_task = loop.create_task(self._watch_files())
            logger.info("Hot reload started")
        except RuntimeError:
            # No event loop running yet, delay start
            logger.info("Hot reload scheduled to start with bot")
            self.watch_task = None

    def stop_watching(self) -> None:
        if self.watch_task and not self.watch_task.done():
            self.watch_task.cancel()
            logger.info("Hot reload stopped")

    async def _watch_files(self) -> None:
        try:
            paths_to_watch = [str(path) for path in self.watched_directories]

            async for changes in awatch(*paths_to_watch):
                await self._handle_changes(changes)

        except asyncio.CancelledError:
            logger.info("File watcher cancelled")
        except Exception as e:
            logger.error(f"Error in file watcher: {e}")

    async def _handle_changes(self, changes: Set[tuple]) -> None:
        plugin_changes = set()

        for change_type, file_path in changes:
            path = Path(file_path)

            # Only handle Python files
            if not file_path.endswith('.py'):
                continue

            # Skip __pycache__ and other unwanted files
            if '__pycache__' in file_path or file_path.endswith('.pyc'):
                continue

            logger.debug(f"File change detected: {change_type.name} - {file_path}")

            # Determine if this is a plugin file
            plugin_name = self._get_plugin_name_from_path(path)
            if plugin_name:
                plugin_changes.add(plugin_name)

        # Reload changed plugins
        for plugin_name in plugin_changes:
            await self._reload_plugin(plugin_name)

    def _get_plugin_name_from_path(self, path: Path) -> str:
        # Try to determine plugin name from file path
        for watch_dir in self.watched_directories:
            try:
                relative_path = path.relative_to(watch_dir)

                # If the file is directly in a plugin directory
                if len(relative_path.parts) >= 1:
                    potential_plugin = relative_path.parts[0]

                    # Check if this directory exists and looks like a plugin
                    plugin_dir = watch_dir / potential_plugin
                    if (plugin_dir.is_dir() and
                        (plugin_dir / "__init__.py").exists()):
                        return potential_plugin

            except ValueError:
                # Path is not relative to this watch directory
                continue

        return None

    async def _reload_plugin(self, plugin_name: str) -> None:
        try:
            logger.info(f"Hot reloading plugin: {plugin_name}")

            # Check if plugin is currently loaded
            if plugin_name in self.bot.plugin_loader.plugins:
                success = await self.bot.plugin_loader.reload_plugin(plugin_name)

                if success:
                    logger.info(f"Successfully hot reloaded plugin: {plugin_name}")

                    # Emit event for successful reload
                    await self.bot.event_system.emit("plugin_reloaded", plugin_name)
                else:
                    logger.error(f"Failed to hot reload plugin: {plugin_name}")
            else:
                # Try to load the plugin if it's not loaded
                success = await self.bot.plugin_loader.load_plugin(plugin_name)
                if success:
                    logger.info(f"Loaded new plugin via hot reload: {plugin_name}")
                    await self.bot.event_system.emit("plugin_loaded", plugin_name)

        except Exception as e:
            logger.error(f"Error during hot reload of {plugin_name}: {e}")

    async def reload_all_plugins(self) -> None:
        logger.info("Hot reloading all plugins...")

        loaded_plugins = list(self.bot.plugin_loader.plugins.keys())

        for plugin_name in loaded_plugins:
            await self._reload_plugin(plugin_name)

        logger.info("Finished reloading all plugins")

    def get_watched_directories(self) -> list[str]:
        return [str(path) for path in self.watched_directories]