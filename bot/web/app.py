import logging
import os
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config.settings import settings

logger = logging.getLogger(__name__)


class WebApp:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.app = FastAPI(
            title="Discord Bot Panel",
            description="Web interface for Discord bot management",
            version="1.0.0"
        )

        # Setup Redis session middleware
        from .redis_session import session_store, RedisSessionMiddleware
        self.session_store = session_store
        self.app.add_middleware(RedisSessionMiddleware, session_store=session_store)

        # Setup paths
        self.web_dir = Path(__file__).parent
        self.templates_dir = self.web_dir / "templates"

        # Create templates directory if it doesn't exist (needed for web interface)
        self.templates_dir.mkdir(exist_ok=True)

        # Setup Jinja2 templates
        self.templates = Jinja2Templates(directory=str(self.templates_dir))

        # Setup authentication
        from .auth import DiscordAuth
        self.auth = DiscordAuth(bot)

        # Setup routes
        self._setup_routes()

        # Server instance
        self._server = None
        self._server_task = None

        # Navigation data for templates
        self.navigation_panels = []

    def register_plugin_static(self, plugin_name: str, static_dir: str) -> None:
        """Register a plugin's static files directory"""
        if os.path.exists(static_dir) and os.path.isdir(static_dir):
            mount_path = f"/static/{plugin_name}"
            self.app.mount(mount_path, StaticFiles(directory=static_dir), name=f"static_{plugin_name}")
            logger.info(f"Registered static files for plugin '{plugin_name}' at {mount_path}")
        else:
            logger.warning(f"Static directory for plugin '{plugin_name}' not found: {static_dir}")

    def _setup_routes(self) -> None:
        @self.app.get("/", response_class=HTMLResponse)
        async def landing_page(request: Request):
            """Landing page route for non-authenticated users"""
            bot_user = self.bot.hikari_bot.get_me()

            context = {
                "request": request,
                "bot_name": bot_user.username if bot_user else "Discord Bot",
                "bot_avatar": str(bot_user.make_avatar_url()) if bot_user and bot_user.make_avatar_url() else None,
                "guild_count": len(self.bot.hikari_bot.cache.get_guilds_view()),
                "is_ready": self.bot.is_ready,
                "auth_configured": self.auth.is_configured(),
            }

            return self.templates.TemplateResponse(request, "landing.html", context)

        @self.app.get("/panel", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard route - requires authentication"""
            # Check authentication if OAuth is configured
            if self.auth.is_configured():
                if not self.auth.is_authenticated(request):
                    return RedirectResponse(url="/auth/login", status_code=302)

            bot_user = self.bot.hikari_bot.get_me()
            current_user = self.auth.get_current_user(request)

            # Get plugin panel information
            plugin_panels = []
            if hasattr(self.bot, 'web_panel_manager'):
                all_panels = self.bot.web_panel_manager.get_all_panel_info()
                # Create list of panels with nav_order for sorting
                panels_with_order = []
                for plugin_name, panel_info in all_panels.items():
                    panels_with_order.append({
                        'name': panel_info['name'],
                        'route': panel_info['route'],
                        'description': panel_info['description'],
                        'icon': panel_info.get('icon'),
                        'nav_order': panel_info.get('nav_order', 999)
                    })

                # Sort by nav_order and create final list
                panels_with_order.sort(key=lambda x: x['nav_order'])
                plugin_panels = [{k: v for k, v in panel.items() if k != 'nav_order'} for panel in panels_with_order]

            context = {
                "request": request,
                "bot_name": bot_user.username if bot_user else "Discord Bot",
                "bot_avatar": str(bot_user.make_avatar_url()) if bot_user and bot_user.make_avatar_url() else None,
                "guild_count": len(self.bot.hikari_bot.cache.get_guilds_view()),
                "is_ready": self.bot.is_ready,
                "plugin_panels": plugin_panels,
                "has_plugin_panels": len(plugin_panels) > 0,
                "current_user": current_user,
                "auth_configured": self.auth.is_configured(),
            }

            return self.templates.TemplateResponse(request, "dashboard.html", context)

        # Authentication routes
        @self.app.get("/auth/login")
        async def login(request: Request):
            """Login route - redirect to Discord OAuth"""
            if not self.auth.is_configured():
                raise HTTPException(status_code=500, detail="OAuth not configured")

            if self.auth.is_authenticated(request):
                return RedirectResponse(url="/panel", status_code=302)

            # Check if there was an auth error to prevent infinite loops
            error = request.query_params.get('error')
            if error:
                raise HTTPException(status_code=400, detail="Authentication failed. Please try again.")

            return await self.auth.authorize_redirect(request)

        @self.app.get("/auth/callback")
        async def auth_callback(request: Request):
            """OAuth callback handler"""
            if not self.auth.is_configured():
                raise HTTPException(status_code=500, detail="OAuth not configured")

            try:
                await self.auth.handle_callback(request)
                return RedirectResponse(url="/panel", status_code=302)
            except Exception as e:
                logger.error(f"Auth callback error: {e}")
                return RedirectResponse(url="/auth/login?error=1", status_code=302)

        @self.app.get("/auth/logout")
        async def logout(request: Request):
            """Logout route"""
            await self.auth.logout(request)
            return RedirectResponse(url="/", status_code=302)

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "ok", "bot_ready": self.bot.is_ready}

    async def start(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Start the web server"""
        try:
            # Initialize Redis connection
            await self.session_store.connect()

            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info"
            )
            self._server = uvicorn.Server(config)

            logger.info(f"Starting web server on {host}:{port}")
            await self._server.serve()

        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the web server"""
        try:
            # Disconnect Redis
            await self.session_store.disconnect()

            if self._server:
                logger.info("Stopping web server...")
                self._server.should_exit = True
                if self._server_task:
                    self._server_task.cancel()
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")