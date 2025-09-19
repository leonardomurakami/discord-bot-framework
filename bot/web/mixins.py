from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from fastapi import FastAPI, APIRouter


class WebPanelMixin(ABC):
    """
    Mixin for plugins that want to provide web panel functionality.

    Plugins can inherit from this mixin to add custom web routes, templates,
    and provide their own web interface panels.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._web_router: Optional[APIRouter] = None

    @abstractmethod
    def get_panel_info(self) -> Dict[str, Any]:
        """
        Return metadata about this plugin's web panel.

        Returns:
            Dict containing:
                - name: Display name for the panel
                - description: Brief description of what the panel does
                - icon: Optional icon class/name
                - route: Base route for the panel (e.g., '/music')
                - nav_order: Optional order in navigation (lower = higher priority)
        """
        pass

    @abstractmethod
    def register_web_routes(self, app: FastAPI) -> None:
        """
        Register web routes with the FastAPI application.

        This method should create and configure all routes, endpoints,
        and static file handlers that the plugin needs.

        Args:
            app: The FastAPI application instance
        """
        pass

    def get_web_router(self) -> APIRouter:
        """
        Get or create an APIRouter for this plugin.

        This is a convenience method that plugins can use to organize
        their routes using FastAPI's APIRouter.
        """
        if self._web_router is None:
            self._web_router = APIRouter(
                prefix=f"/plugin/{self.name}",
                tags=[self.name]
            )
        return self._web_router

    def register_router_with_app(self, app: FastAPI) -> None:
        """
        Register this plugin's router with the FastAPI app.

        Call this in register_web_routes() after setting up routes.
        """
        if self._web_router:
            app.include_router(self._web_router)

    def get_template_directory(self) -> Optional[str]:
        """
        Return the directory path for plugin-specific templates.

        Override this to provide custom templates for your plugin.
        Defaults to 'templates' subdirectory in plugin directory.
        """
        import os
        import inspect

        # Get the plugin's source file path
        plugin_file = inspect.getfile(self.__class__)
        plugin_dir = os.path.dirname(plugin_file)
        template_dir = os.path.join(plugin_dir, 'templates')
        return template_dir if os.path.exists(template_dir) else None

    def get_static_directory(self) -> Optional[str]:
        """
        Return the directory path for plugin-specific static files.

        Override this to provide custom static files (CSS, JS, images).
        Defaults to 'static' subdirectory in plugin directory.
        """
        import os
        plugin_dir = os.path.dirname(self.__module__.replace('.', '/'))
        static_dir = os.path.join(plugin_dir, 'static')
        return static_dir if os.path.exists(static_dir) else None

    def render_plugin_template(self, request, template_name: str, context: dict = None):
        """
        Render a plugin template using hybrid template loading.

        This method creates a Jinja2Templates instance that searches both:
        1. Plugin's local template directory (for plugin-specific templates)
        2. Bot core template directory (for shared templates like plugin_base.html)

        Args:
            request: FastAPI request object
            template_name: Name of the template file
            context: Additional context variables

        Returns:
            Jinja2 TemplateResponse
        """
        from fastapi.templating import Jinja2Templates
        from jinja2 import FileSystemLoader, Environment
        import os
        from pathlib import Path

        # Build list of template directories to search
        template_dirs = []

        # 1. Plugin's template directory (highest priority)
        plugin_template_dir = self.get_template_directory()
        if plugin_template_dir and os.path.exists(plugin_template_dir):
            template_dirs.append(plugin_template_dir)

        # 2. Bot core template directory (fallback for shared templates)
        if hasattr(self.bot, 'web_panel_manager'):
            core_template_dir = str(self.bot.web_panel_manager.web_app.templates_dir)
            if os.path.exists(core_template_dir):
                template_dirs.append(core_template_dir)

        if not template_dirs:
            raise ValueError(f"No template directories found for plugin {self.name}")

        # Create Jinja2 environment with multiple template directories
        loader = FileSystemLoader(template_dirs)
        env = Environment(loader=loader)

        # Create FastAPI-compatible templates instance
        templates = Jinja2Templates(env=env)

        # Build context with plugin and bot info
        plugin_info = self.get_panel_info()
        bot_user = self.bot.hikari_bot.get_me()
        bot_avatar = None
        if bot_user and bot_user.make_avatar_url():
            bot_avatar = str(bot_user.make_avatar_url())

        current_user = None
        auth_configured = False
        if hasattr(self.bot, 'web_panel_manager'):
            web_app = getattr(self.bot.web_panel_manager, 'web_app', None)
            if web_app and hasattr(web_app, 'auth'):
                auth_configured = web_app.auth.is_configured()
                current_user = web_app.auth.get_current_user(request)

        base_context = {
            "request": request,
            "plugin_name": plugin_info.get('name', self.name),
            "plugin_description": plugin_info.get('description', ''),
            "plugin_icon": plugin_info.get('icon', ''),
            "bot_name": getattr(bot_user, 'username', 'Discord Bot') if bot_user else 'Discord Bot',
            "bot_avatar": bot_avatar,
            "current_user": current_user,
            "auth_configured": auth_configured,
        }

        # Add plugin panels for sidebar navigation
        if hasattr(self.bot, 'web_panel_manager'):
            all_panels = self.bot.web_panel_manager.get_all_panel_info()
            panels_with_order = []
            for plugin_name, panel_info in all_panels.items():
                panels_with_order.append({
                    'name': panel_info['name'],
                    'route': panel_info['route'],
                    'description': panel_info['description'],
                    'icon': panel_info.get('icon'),
                    'nav_order': panel_info.get('nav_order', 999)
                })
            panels_with_order.sort(key=lambda x: x['nav_order'])
            base_context['plugin_panels'] = [{k: v for k, v in panel.items() if k != 'nav_order'} for panel in panels_with_order]
            base_context['has_plugin_panels'] = len(panels_with_order) > 0

        # Merge with provided context
        if context:
            base_context.update(context)

        return templates.TemplateResponse(request, template_name, base_context)
