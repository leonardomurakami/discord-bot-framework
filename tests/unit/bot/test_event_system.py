"""Tests for event system functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.core.event_system import EventSystem, event_listener


class TestEventSystem:
    """Test EventSystem functionality."""

    def test_event_system_creation(self):
        """Test creating an EventSystem instance."""
        event_system = EventSystem()

        assert event_system._listeners == {}
        assert event_system._middleware == []

    def test_add_listener(self):
        """Test adding an event listener."""
        event_system = EventSystem()
        listener = MagicMock()
        listener.__name__ = "test_listener"
        listener.__name__ = "test_listener"

        event_system.add_listener("test_event", listener)

        assert "test_event" in event_system._listeners
        assert listener in event_system._listeners["test_event"]

    def test_add_multiple_listeners(self):
        """Test adding multiple listeners for the same event."""
        event_system = EventSystem()
        listener1 = MagicMock()
        listener1.__name__ = "listener1"
        listener2 = MagicMock()
        listener2.__name__ = "listener2"

        event_system.add_listener("test_event", listener1)
        event_system.add_listener("test_event", listener2)

        assert len(event_system._listeners["test_event"]) == 2
        assert listener1 in event_system._listeners["test_event"]
        assert listener2 in event_system._listeners["test_event"]

    def test_remove_listener(self):
        """Test removing an event listener."""
        event_system = EventSystem()
        listener = MagicMock()
        listener.__name__ = "test_listener"
        listener.__name__ = "test_listener"

        event_system.add_listener("test_event", listener)
        event_system.remove_listener("test_event", listener)

        assert listener not in event_system._listeners.get("test_event", [])

    def test_remove_nonexistent_listener(self):
        """Test removing a listener that doesn't exist."""
        event_system = EventSystem()
        listener = MagicMock()
        listener.__name__ = "test_listener"

        # Should not raise an exception
        event_system.remove_listener("test_event", listener)

    @pytest.mark.asyncio
    async def test_emit_event_with_listeners(self):
        """Test emitting an event with listeners."""
        event_system = EventSystem()
        listener = AsyncMock()

        event_system.add_listener("test_event", listener)

        event_data = {"test": "data"}
        await event_system.emit("test_event", event_data)

        listener.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_emit_event_no_listeners(self):
        """Test emitting an event with no listeners."""
        event_system = EventSystem()

        # Should not raise an exception
        await event_system.emit("test_event", {"test": "data"})

    @pytest.mark.asyncio
    async def test_emit_event_multiple_listeners(self):
        """Test emitting an event with multiple listeners."""
        event_system = EventSystem()
        listener1 = AsyncMock()
        listener2 = AsyncMock()

        event_system.add_listener("test_event", listener1)
        event_system.add_listener("test_event", listener2)

        event_data = {"test": "data"}
        await event_system.emit("test_event", event_data)

        listener1.assert_called_once_with(event_data)
        listener2.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_emit_event_with_error_in_listener(self):
        """Test emitting an event when a listener raises an error."""
        event_system = EventSystem()

        def error_listener(event_data):
            raise Exception("Listener error")

        working_listener = AsyncMock()

        event_system.add_listener("test_event", error_listener)
        event_system.add_listener("test_event", working_listener)

        # Should not prevent other listeners from being called
        await event_system.emit("test_event", {"test": "data"})

        working_listener.assert_called_once()

    def test_add_middleware(self):
        """Test adding middleware to the event system."""
        event_system = EventSystem()
        middleware = MagicMock()
        middleware.__name__ = "test_middleware"

        event_system.add_middleware(middleware)

        assert middleware in event_system._middleware

    @pytest.mark.asyncio
    async def test_emit_with_middleware(self):
        """Test emitting events with middleware."""
        event_system = EventSystem()
        middleware = AsyncMock()
        middleware.__name__ = "test_middleware"
        listener = AsyncMock()
        listener.__name__ = "test_listener"

        event_system.add_middleware(middleware)
        event_system.add_listener("test_event", listener)

        event_data = {"test": "data"}
        await event_system.emit("test_event", event_data)

        # Middleware is called twice: once for "pre" and once for "post"
        assert middleware.call_count == 2
        listener.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_can_modify_event(self):
        """Test that middleware can access event context."""
        event_system = EventSystem()

        async def middleware_with_context(event_context, phase):
            # Middleware receives event_context dict and phase ("pre" or "post")
            assert "event_name" in event_context
            assert "args" in event_context
            assert "kwargs" in event_context
            assert phase in ["pre", "post"]

        middleware_with_context.__name__ = "test_middleware"
        listener = AsyncMock()
        listener.__name__ = "test_listener"

        event_system.add_middleware(middleware_with_context)
        event_system.add_listener("test_event", listener)

        event_data = {"test": "data"}
        await event_system.emit("test_event", event_data)

        # Listener should be called with the original event data
        listener.assert_called_once_with(event_data)

    def test_get_listeners(self):
        """Test getting listeners for an event."""
        event_system = EventSystem()
        listener1 = MagicMock()
        listener1.__name__ = "listener1"
        listener2 = MagicMock()
        listener2.__name__ = "listener2"

        event_system.add_listener("test_event", listener1)
        event_system.add_listener("test_event", listener2)

        listeners = event_system.get_listeners("test_event")

        assert len(listeners) == 2
        assert listener1 in listeners
        assert listener2 in listeners

    def test_get_listeners_nonexistent_event(self):
        """Test getting listeners for a nonexistent event."""
        event_system = EventSystem()

        listeners = event_system.get_listeners("nonexistent_event")

        assert listeners == []

    def test_has_listeners(self):
        """Test checking if an event has listeners."""
        event_system = EventSystem()
        listener = MagicMock()
        listener.__name__ = "test_listener"

        listeners = event_system.get_listeners("test_event")
        assert len(listeners) == 0

        event_system.add_listener("test_event", listener)

        listeners = event_system.get_listeners("test_event")
        assert len(listeners) > 0

    def test_remove_all_listeners(self):
        """Test removing all listeners for an event."""
        event_system = EventSystem()
        listener1 = MagicMock()
        listener1.__name__ = "listener1"
        listener2 = MagicMock()
        listener2.__name__ = "listener2"

        event_system.add_listener("test_event", listener1)
        event_system.add_listener("test_event", listener2)

        event_system.remove_all_listeners("test_event")

        listeners = event_system.get_listeners("test_event")
        assert len(listeners) == 0

    @pytest.mark.asyncio
    async def test_concurrent_event_emission(self):
        """Test emitting multiple events concurrently."""
        event_system = EventSystem()
        listener = AsyncMock()

        event_system.add_listener("test_event", listener)

        # Emit multiple events concurrently
        tasks = []
        for i in range(5):
            task = asyncio.create_task(event_system.emit("test_event", {"index": i}))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Listener should have been called 5 times
        assert listener.call_count == 5


class TestEventListenerDecorator:
    """Test event_listener decorator functionality."""

    def test_event_listener_decorator_function(self):
        """Test the event_listener decorator on a function."""

        @event_listener("test_event")
        def test_handler(event_data):
            pass

        assert hasattr(test_handler, "_event_listener")
        assert test_handler._event_listener == "test_event"

    def test_event_listener_decorator_method(self):
        """Test the event_listener decorator on a method."""

        class TestClass:
            @event_listener("test_event")
            def test_handler(self, event_data):
                pass

        instance = TestClass()
        assert hasattr(instance.test_handler, "_event_listener")
        assert instance.test_handler._event_listener == "test_event"

    @pytest.mark.asyncio
    async def test_event_listener_decorator_async(self):
        """Test the event_listener decorator on an async function."""

        @event_listener("test_event")
        async def test_handler(event_data):
            return "handled"

        assert hasattr(test_handler, "_event_listener")
        assert test_handler._event_listener == "test_event"

        # Test that the function still works
        result = await test_handler({"test": "data"})
        assert result == "handled"
