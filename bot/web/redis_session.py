import json
import logging
import uuid
from typing import Any, Dict, MutableMapping, Optional
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response
from config.settings import settings

# Try to import Redis, fall back to None if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Session storage will use fallback method.")

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """Redis-based session store for FastAPI"""

    def __init__(self, redis_url: str, session_prefix: str = "session:", ttl: int = 86400):
        self.redis_url = redis_url
        self.session_prefix = session_prefix
        self.ttl = ttl
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            logger.info("Redis not available, using fallback session storage")
            self.redis_client = None
            return

        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8"
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis session store connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Fallback to None - will use in-memory sessions
            self.redis_client = None

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis session store disconnected")

    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session"""
        return f"{self.session_prefix}{session_id}"

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session data from Redis"""
        if not self.redis_client:
            return {}

        try:
            key = self._get_session_key(session_id)
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return {}
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return {}

    async def set_session(self, session_id: str, data: Dict[str, Any]):
        """Set session data in Redis"""
        if not self.redis_client:
            return

        try:
            key = self._get_session_key(session_id)
            json_data = json.dumps(data, default=str)
            await self.redis_client.setex(key, self.ttl, json_data)
        except Exception as e:
            logger.error(f"Error setting session {session_id}: {e}")

    async def delete_session(self, session_id: str):
        """Delete session from Redis"""
        if not self.redis_client:
            return

        try:
            key = self._get_session_key(session_id)
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")

    async def extend_session(self, session_id: str):
        """Extend session TTL"""
        if not self.redis_client:
            return

        try:
            key = self._get_session_key(session_id)
            await self.redis_client.expire(key, self.ttl)
        except Exception as e:
            logger.error(f"Error extending session {session_id}: {e}")


class RedisSession(MutableMapping):
    """Session wrapper that uses Redis for storage"""

    def __init__(self, session_store: RedisSessionStore, session_id: str):
        self.session_store = session_store
        self.session_id = session_id
        self._data: Dict[str, Any] = {}
        self._loaded = False
        self._modified = False

    async def load(self):
        """Load session data from Redis"""
        if not self._loaded:
            self._data = await self.session_store.get_session(self.session_id)
            self._loaded = True

    async def save(self):
        """Save session data to Redis if modified"""
        if self._modified:
            await self.session_store.set_session(self.session_id, self._data)
            self._modified = False

    async def clear(self):
        """Clear session data"""
        self._data.clear()
        self._modified = True
        await self.session_store.delete_session(self.session_id)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self._modified = True

    def __delitem__(self, key):
        del self._data[key]
        self._modified = True

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def update(self, *args, **kwargs):
        self._data.update(*args, **kwargs)
        self._modified = True


class RedisSessionMiddleware:
    """Custom session middleware that uses Redis"""

    def __init__(self, app, session_store: RedisSessionStore, session_cookie: str = "session"):
        self.app = app
        self.session_store = session_store
        self.session_cookie = session_cookie

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        session_id = request.cookies.get(self.session_cookie)

        if not session_id:
            session_id = str(uuid.uuid4())

        # Create Redis session
        session = RedisSession(self.session_store, session_id)
        await session.load()

        # Add session to request
        scope["session"] = session

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Save session before sending response
                await session.save()

                # Extend session TTL if it exists
                if session._data:
                    await self.session_store.extend_session(session_id)

                # Set session cookie
                response = Response()
                response.set_cookie(
                    key=self.session_cookie,
                    value=session_id,
                    max_age=self.session_store.ttl,
                    httponly=True,
                    secure=False,  # Set to True in production with HTTPS
                    samesite="lax"
                )

                # Add cookie to headers
                if "set-cookie" in response.headers:
                    if "headers" not in message:
                        message["headers"] = []
                    message["headers"].append([
                        b"set-cookie",
                        response.headers["set-cookie"].encode()
                    ])

            await send(message)

        await self.app(scope, receive, send_wrapper)


# Global session store instance
session_store = RedisSessionStore(
    redis_url=settings.redis_url,
    session_prefix=settings.redis_session_prefix,
    ttl=settings.redis_session_ttl
)