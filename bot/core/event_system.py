import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class EventSystem:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable]] = {}
        self._middleware: list[Callable] = []

    def add_middleware(self, middleware: Callable) -> None:
        self._middleware.append(middleware)
        logger.debug(f"Added middleware: {middleware.__name__}")

    def remove_middleware(self, middleware: Callable) -> None:
        if middleware in self._middleware:
            self._middleware.remove(middleware)
            logger.debug(f"Removed middleware: {middleware.__name__}")

    def listen(self, event_name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_listener(event_name, func)
            return func

        return decorator

    def add_listener(self, event_name: str, callback: Callable) -> None:
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)
        logger.debug(f"Added listener for {event_name}: {callback.__name__}")

    def remove_listener(self, event_name: str, callback: Callable) -> None:
        if event_name in self._listeners:
            try:
                self._listeners[event_name].remove(callback)
                logger.debug(f"Removed listener for {event_name}: {callback.__name__}")
            except ValueError:
                logger.warning(
                    f"Listener {callback.__name__} not found for {event_name}"
                )

    def remove_all_listeners(self, event_name: str) -> None:
        if event_name in self._listeners:
            self._listeners[event_name].clear()
            logger.debug(f"Removed all listeners for {event_name}")

    async def emit(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        if event_name not in self._listeners:
            return

        # Create event context
        event_context = {
            "event_name": event_name,
            "args": args,
            "kwargs": kwargs,
            "stopped": False,
        }

        # Run middleware (pre-processing)
        for middleware in self._middleware:
            try:
                result = await self._call_maybe_async(middleware, event_context, "pre")
                if result is False or event_context.get("stopped"):
                    logger.debug(f"Event {event_name} stopped by middleware")
                    return
            except Exception as e:
                logger.error(f"Error in middleware {middleware.__name__}: {e}")

        # Execute listeners
        tasks = []
        for listener in self._listeners[event_name]:
            tasks.append(self._execute_listener(listener, *args, **kwargs))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    listener_name = self._listeners[event_name][i].__name__
                    logger.error(
                        f"Error in listener {listener_name} for {event_name}: {result}"
                    )

        # Run middleware (post-processing)
        for middleware in self._middleware:
            try:
                await self._call_maybe_async(middleware, event_context, "post")
            except Exception as e:
                logger.error(f"Error in middleware {middleware.__name__} (post): {e}")

    async def _execute_listener(
        self, listener: Callable, *args: Any, **kwargs: Any
    ) -> None:
        try:
            await self._call_maybe_async(listener, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing listener {listener.__name__}: {e}")
            raise

    async def _call_maybe_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    def get_listeners(self, event_name: str) -> list[Callable]:
        return self._listeners.get(event_name, []).copy()

    def get_all_events(self) -> list[str]:
        return list(self._listeners.keys())


# Decorator for event listeners
def event_listener(event_name: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        func._event_listener = event_name
        return func

    return decorator


# Middleware decorator
def middleware(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(event_context: dict[str, Any], phase: str) -> Any:
        return await func(event_context, phase)

    wrapper._is_middleware = True
    return wrapper
