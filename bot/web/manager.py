import asyncio
import logging
from typing import Any

from config.settings import settings

from .app import WebApp

logger = logging.getLogger(__name__)


class WebPanelManager:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.web_app = WebApp(bot)
        self.registered_panels: dict[str, Any] = {}
        self._server_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the web panel server"""
        try:
            # Start the web server in the background
            self._server_task = asyncio.create_task(self.web_app.start(host=settings.web_host, port=settings.web_port))

            logger.info(f"Web panel available at http://{settings.web_host}:{settings.web_port}")

        except Exception as e:
            logger.error(f"Failed to start web panel: {e}")
            raise

    async def stop(self) -> None:
        """Stop the web panel server"""
        try:
            if self._server_task and not self._server_task.done():
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass

            await self.web_app.stop()
            logger.info("Web panel stopped")

        except Exception as e:
            logger.error(f"Error stopping web panel: {e}")

    def register_plugin_panel(self, plugin_name: str, plugin: Any) -> None:
        """Register a plugin's web panel interface"""
        from .mixins import WebPanelMixin

        if not isinstance(plugin, WebPanelMixin):
            logger.warning(f"Plugin {plugin_name} does not inherit from WebPanelMixin")
            return

        try:
            # Validate plugin panel info
            panel_info = plugin.get_panel_info()
            required_fields = ["name", "description", "route"]
            for field in required_fields:
                if field not in panel_info:
                    raise ValueError(f"Plugin {plugin_name} missing required panel info field: {field}")

            # Register web routes
            plugin.register_web_routes(self.web_app.app)

            # Register plugin static files if available
            static_dir = plugin.get_static_directory()
            if static_dir:
                self.web_app.register_plugin_static(plugin_name, static_dir)

            # Store plugin and panel info
            self.registered_panels[plugin_name] = {"plugin": plugin, "panel_info": panel_info}

            logger.info(f"Registered web panel for plugin: {plugin_name} at {panel_info['route']}")

            # Update navigation
            self._update_navigation()

        except Exception as e:
            logger.error(f"Failed to register web panel for {plugin_name}: {e}")

    def unregister_plugin_panel(self, plugin_name: str) -> None:
        """Unregister a plugin's web panel interface"""
        if plugin_name in self.registered_panels:
            del self.registered_panels[plugin_name]
            logger.info(f"Unregistered web panel for plugin: {plugin_name}")

            # Update navigation
            self._update_navigation()

    def get_registered_panels(self) -> list[str]:
        """Get list of registered plugin panels"""
        return list(self.registered_panels.keys())

    def get_panel_info(self, plugin_name: str) -> dict[str, Any]:
        """Get panel info for a specific plugin"""
        if plugin_name in self.registered_panels:
            return self.registered_panels[plugin_name]["panel_info"]
        return {}

    def get_all_panel_info(self) -> dict[str, dict[str, Any]]:
        """Get panel info for all registered plugins"""
        return {name: data["panel_info"] for name, data in self.registered_panels.items()}

    def _update_navigation(self) -> None:
        """Update the navigation menu with current panels"""
        # Sort panels by nav_order if specified
        sorted_panels = sorted(self.registered_panels.items(), key=lambda x: x[1]["panel_info"].get("nav_order", 999))

        # Store navigation data for templates
        self.web_app.navigation_panels = sorted_panels

    def has_panels(self) -> bool:
        """Check if any plugin panels are registered"""
        return len(self.registered_panels) > 0
