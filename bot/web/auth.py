import logging
from typing import Optional, Dict, Any
import aiohttp
from fastapi import Request, HTTPException, status
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from config.settings import settings

logger = logging.getLogger(__name__)


class DiscordAuth:
    """Discord OAuth2 authentication handler"""

    def __init__(self, bot: Any):
        self.bot = bot
        self.oauth = None
        self.discord_client = None

        if settings.discord_client_id and settings.discord_client_secret:
            self._setup_oauth()
        else:
            logger.warning("Discord OAuth2 credentials not configured. Web authentication disabled.")

    def _setup_oauth(self):
        """Setup OAuth2 client"""
        self.oauth = OAuth()

        # Register Discord OAuth2 client according to authlib docs
        self.discord_client = self.oauth.register(
            name='discord',
            client_id=settings.discord_client_id,
            client_secret=settings.discord_client_secret,
            access_token_url='https://discord.com/api/oauth2/token',
            authorize_url='https://discord.com/api/oauth2/authorize',
            api_base_url='https://discord.com/api/',
            client_kwargs={
                'scope': 'identify guilds'
            }
        )

    def is_configured(self) -> bool:
        """Check if OAuth is properly configured"""
        return self.oauth is not None and self.discord_client is not None

    async def authorize_redirect(self, request: Request):
        """Create Discord OAuth2 authorization redirect"""
        if not self.is_configured():
            raise HTTPException(status_code=500, detail="OAuth not configured")

        try:
            redirect_uri = settings.discord_redirect_uri
            return await self.discord_client.authorize_redirect(request, redirect_uri)

        except Exception as e:
            logger.error(f"Error creating authorization redirect: {e}")
            raise HTTPException(status_code=500, detail=f"OAuth configuration error: {str(e)}")

    async def handle_callback(self, request: Request) -> Dict[str, Any]:
        """Handle OAuth2 callback and exchange code for token"""
        if not self.is_configured():
            raise HTTPException(status_code=500, detail="OAuth not configured")

        try:
            # Exchange code for token
            token = await self.discord_client.authorize_access_token(request)

            # Get user info
            user_info = await self.get_user_info(token['access_token'])

            # Get user guilds
            user_guilds = await self.get_user_guilds(token['access_token'])

            # Get bot's guilds via Discord API instead of cache
            bot_guilds = await self.get_bot_guilds()
            bot_guild_ids = {str(guild['id']) for guild in bot_guilds}

            logger.debug(f"Bot is in {len(bot_guild_ids)} guilds: {[guild['name'] for guild in bot_guilds]}")
            logger.debug(f"User is in {len(user_guilds)} guilds: {[guild['name'] for guild in user_guilds]}")

            accessible_guilds = [
                guild for guild in user_guilds
                if str(guild['id']) in bot_guild_ids
            ]
            logger.debug(f"User has access to {len(accessible_guilds)} guilds: {[guild['name'] for guild in accessible_guilds]}")

            # Store in session
            session_data = {
                'user': user_info,
                'guilds': accessible_guilds,
                'access_token': token['access_token'],
                'authenticated': True
            }

            # Store in session
            request.session.update(session_data)

            return session_data

        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            raise HTTPException(status_code=400, detail="Authentication failed")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Discord user information"""
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {access_token}'}
            async with session.get('https://discord.com/api/users/@me', headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    raise HTTPException(status_code=401, detail="Invalid token")

    async def get_user_guilds(self, access_token: str) -> list:
        """Get Discord user's guilds"""
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {access_token}'}
            async with session.get('https://discord.com/api/users/@me/guilds', headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    raise HTTPException(status_code=401, detail="Could not fetch guilds")

    async def get_bot_guilds(self) -> list:
        """Get bot's guilds from Discord API using bot token"""
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bot {settings.discord_token}'}
            async with session.get('https://discord.com/api/users/@me/guilds', headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Failed to fetch bot guilds: {resp.status}")
                    # Fallback to cache if API fails
                    cache_guilds = self.bot.hikari_bot.cache.get_guilds_view()
                    return [{'id': guild_id, 'name': 'Unknown'} for guild_id in cache_guilds.keys()]

    def get_current_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get current authenticated user from session"""
        if request.session.get('authenticated'):
            return {
                'user': request.session.get('user'),
                'guilds': request.session.get('guilds'),
                'access_token': request.session.get('access_token')
            }
        return None

    def is_authenticated(self, request: Request) -> bool:
        """Check if user is authenticated"""
        return request.session.get('authenticated', False)

    async def logout(self, request: Request):
        """Logout user by clearing session and revoking token"""
        # Get access token before clearing session
        access_token = request.session.get('access_token')

        # Revoke token with Discord if available
        if access_token and self.is_configured():
            try:
                await self.revoke_token(access_token)
                logger.info("Discord token revoked successfully")
            except Exception as e:
                logger.warning(f"Failed to revoke Discord token: {e}")

        # Clear session data (handle both Redis and regular sessions)
        if hasattr(request.session, 'clear') and callable(request.session.clear):
            # For Redis sessions, call clear() which deletes from Redis
            if hasattr(request.session, '_data'):
                await request.session.clear()
            else:
                request.session.clear()
        else:
            # Fallback: manually clear all keys
            keys_to_remove = list(request.session.keys())
            for key in keys_to_remove:
                del request.session[key]

        logger.info("Session cleared successfully")

    async def revoke_token(self, access_token: str):
        """Revoke Discord access token"""
        async with aiohttp.ClientSession() as session:
            # Discord token revocation endpoint
            data = {
                'token': access_token,
                'client_id': settings.discord_client_id,
                'client_secret': settings.discord_client_secret
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with session.post(
                'https://discord.com/api/oauth2/token/revoke',
                data=data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(
                        status_code=resp.status,
                        detail=f"Failed to revoke token: {await resp.text()}"
                    )

    def require_auth(self, request: Request) -> Dict[str, Any]:
        """Require authentication, raise HTTP 401 if not authenticated"""
        user_data = self.get_current_user(request)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return user_data

    def require_guild_access(self, request: Request, guild_id: str) -> bool:
        """Check if user has access to a specific guild"""
        user_data = self.require_auth(request)
        user_guilds = user_data.get('guilds', [])

        # Check if user is in the guild
        for guild in user_guilds:
            if str(guild['id']) == str(guild_id):
                return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for this guild"
        )

    def has_guild_permission(self, request: Request, guild_id: str, permission: str) -> bool:
        """Check if user has specific permission in a guild"""
        user_data = self.require_auth(request)
        user_guilds = user_data.get('guilds', [])

        # Find the guild
        for guild in user_guilds:
            if str(guild['id']) == str(guild_id):
                permissions = guild.get('permissions', 0)

                # Basic permission checking (you can extend this)
                permission_values = {
                    'administrator': 0x8,
                    'manage_guild': 0x20,
                    'manage_channels': 0x10,
                    'manage_roles': 0x10000000,
                    'manage_messages': 0x2000,
                }

                required_permission = permission_values.get(permission, 0)
                return (permissions & required_permission) != 0 or (permissions & 0x8) != 0  # Admin override

        return False