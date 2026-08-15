## Purpose
Provides a web-based control panel framework for Discord bot management using FastAPI, with Redis-backed session storage, Discord OAuth authentication, and plugin-extensible web interfaces.

## Requirements

### Requirement: WebApp Initialization
The framework SHALL provide a WebApp class that initializes a FastAPI application with Jinja2 templates, Redis session middleware, and Discord OAuth authentication.

#### Scenario: Initialize WebApp with all components
- **WHEN** WebApp is instantiated with a bot instance
- **THEN** it SHALL create a FastAPI app with title "Discord Bot Panel", setup RedisSessionMiddleware with session_store, create templates directory, initialize DiscordAuth, and setup core routes

### Requirement: Redis Session Storage
The framework SHALL provide Redis-backed session storage with graceful fallback to in-memory sessions when Redis is unavailable.

#### Scenario: Redis connection succeeds
- **WHEN** RedisSessionStore.connect() is called and Redis is available
- **THEN** it SHALL establish a Redis connection, test with ping(), and log successful connection

#### Scenario: Redis connection fails
- **WHEN** RedisSessionStore.connect() is called and Redis is unavailable
- **THEN** it SHALL log an error, set redis_client to None, and allow session operations to continue with in-memory fallback

### Requirement: Discord OAuth Authentication
The framework SHALL provide Discord OAuth2 authentication flow with token exchange, user info retrieval, and guild access validation.

#### Scenario: User initiates OAuth login
- **WHEN** a user accesses /auth/login
- **THEN** DiscordAuth SHALL redirect to Discord OAuth authorize URL with configured client_id, scopes (identify, guilds), and redirect_uri

#### Scenario: OAuth callback handling
- **WHEN** Discord redirects to /auth/callback with authorization code
- **THEN** DiscordAuth SHALL exchange code for access token, fetch user info and guilds, filter guilds to those the bot is in, store session data, and redirect to /panel

#### Scenario: Token revocation on logout
- **WHEN** user accesses /auth/logout
- **THEN** DiscordAuth SHALL revoke the Discord access token, clear session data from Redis, and redirect to landing page

### Requirement: Web Panel Manager
The framework SHALL provide a WebPanelManager to register plugin panels, manage the web server lifecycle, and handle static asset mounting.

#### Scenario: Register plugin panel
- **WHEN** a plugin calls register_plugin_panel with plugin_name and plugin instance
- **THEN** WebPanelManager SHALL validate the plugin inherits WebPanelMixin, validate panel_info has required fields (name, description, route), call register_web_routes, mount static files if available, and update navigation

#### Scenario: Start web server
- **WHEN** WebPanelManager.start() is called
- **THEN** it SHALL initialize Redis connection, create background asyncio task for uvicorn server, and log the server URL

#### Scenario: Stop web server
- **WHEN** WebPanelManager.stop() is called
- **THEN** it SHALL cancel the server task, stop uvicorn server, disconnect Redis, and log shutdown

### Requirement: Web Panel Mixin
The framework SHALL provide a WebPanelMixin for plugins to define panel metadata, register routes, and render templates with hybrid template loading.

#### Scenario: Plugin implements get_panel_info
- **WHEN** a plugin inherits WebPanelMixin and implements get_panel_info()
- **THEN** it SHALL return a dict with name, description, route, icon (optional), nav_order (optional), and requires_discord_admin (optional)

#### Scenario: Plugin registers web routes
- **WHEN** a plugin implements register_web_routes(app)
- **THEN** it SHALL register FastAPI routes with the provided app instance, optionally using get_web_router() for APIRouter organization

#### Scenario: Plugin renders template
- **WHEN** a plugin calls render_plugin_template(request, template_name, context)
- **THEN** it SHALL create Jinja2 environment with plugin template directory and bot core template directory, include bot/user context, filter plugin panels by admin access, and return TemplateResponse

### Requirement: Session Middleware
The framework SHALL provide RedisSessionMiddleware that intercepts HTTP requests, manages session cookies, and persists session data to Redis.

#### Scenario: Request with existing session cookie
- **WHEN** a request arrives with a valid session cookie
- **THEN** middleware SHALL load session data from Redis, attach to request scope, extend TTL on response, and set cookie header

#### Scenario: Request without session cookie
- **WHEN** a request arrives without a session cookie
- **THEN** middleware SHALL generate new UUID session ID, create empty RedisSession, attach to request scope, and set cookie header on response

### Requirement: Route Protection
The framework SHALL provide authentication guards for web routes to require Discord admin permissions.

#### Scenario: Access panel without authentication
- **WHEN** an unauthenticated user accesses /panel
- **THEN** the route SHALL redirect to /auth/login if OAuth is configured

#### Scenario: Access admin-restricted panel
- **WHEN** a user accesses a panel with requires_discord_admin=True but lacks Discord admin permissions
- **THEN** the panel SHALL be filtered from navigation and access SHALL be denied
