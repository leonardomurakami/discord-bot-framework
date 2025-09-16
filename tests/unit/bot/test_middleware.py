"""Tests for bot/middleware/ modules"""

import time
from unittest.mock import patch

import pytest

from bot.middleware.analytics import AnalyticsMiddleware, analytics_middleware
from bot.middleware.error_handler import (
    ErrorHandlerMiddleware,
    error_handler_middleware,
)
from bot.middleware.logging import LoggingMiddleware, logging_middleware


class TestLoggingMiddleware:
    """Test LoggingMiddleware functionality."""

    def setup_method(self):
        """Setup test instance."""
        self.middleware = LoggingMiddleware()

    @pytest.mark.asyncio
    async def test_pre_phase_logs_event_start(self):
        """Test that pre phase logs event start and tracks time."""
        event_context = {"event_name": "test_event"}

        with patch("bot.middleware.logging.logger") as mock_logger:
            await self.middleware(event_context, "pre")

            mock_logger.debug.assert_called_once_with("Event started: test_event")
            assert "test_event" in self.middleware.start_times

    @pytest.mark.asyncio
    async def test_post_phase_logs_event_completion_with_duration(self):
        """Test that post phase logs completion with duration."""
        event_context = {"event_name": "test_event"}

        # Set up start time
        start_time = time.time() - 0.5  # 500ms ago
        self.middleware.start_times["test_event"] = start_time

        with patch("bot.middleware.logging.logger") as mock_logger:
            await self.middleware(event_context, "post")

            # Should log completion with duration
            calls = mock_logger.debug.call_args_list
            assert len(calls) == 1
            call_args = calls[0][0][0]
            assert "Event completed: test_event" in call_args
            assert "took" in call_args
            assert "s)" in call_args

            # Start time should be removed
            assert "test_event" not in self.middleware.start_times

    @pytest.mark.asyncio
    async def test_post_phase_logs_completion_without_start_time(self):
        """Test post phase when no start time exists."""
        event_context = {"event_name": "test_event"}

        with patch("bot.middleware.logging.logger") as mock_logger:
            await self.middleware(event_context, "post")

            mock_logger.debug.assert_called_once_with("Event completed: test_event")

    @pytest.mark.asyncio
    async def test_handles_missing_event_name(self):
        """Test middleware handles missing event name gracefully."""
        event_context = {}

        # Should not raise exception
        await self.middleware(event_context, "pre")
        await self.middleware(event_context, "post")

    @pytest.mark.asyncio
    async def test_other_phases_ignored(self):
        """Test that other phases are ignored."""
        event_context = {"event_name": "test_event"}

        with patch("bot.middleware.logging.logger") as mock_logger:
            await self.middleware(event_context, "unknown_phase")

            mock_logger.debug.assert_not_called()

    def test_global_instance_exists(self):
        """Test that global logging middleware instance exists."""
        assert logging_middleware is not None
        assert isinstance(logging_middleware, LoggingMiddleware)


class TestErrorHandlerMiddleware:
    """Test ErrorHandlerMiddleware functionality."""

    def setup_method(self):
        """Setup test instance."""
        self.middleware = ErrorHandlerMiddleware()

    @pytest.mark.asyncio
    async def test_post_phase_logs_error(self):
        """Test that post phase logs errors when present."""
        test_error = ValueError("Test error message")
        event_context = {"event_name": "test_event", "error": test_error}

        with patch("bot.middleware.error_handler.logger") as mock_logger:
            await self.middleware(event_context, "post")

            # Check error was logged
            error_calls = [call for call in mock_logger.error.call_args_list]
            assert len(error_calls) == 2  # One for error, one for traceback

            # Check error message
            assert "Error in event test_event: Test error message" in str(error_calls[0])

            # Check traceback
            assert "Traceback:" in str(error_calls[1])

    @pytest.mark.asyncio
    async def test_post_phase_no_error(self):
        """Test post phase when no error exists."""
        event_context = {"event_name": "test_event"}

        with patch("bot.middleware.error_handler.logger") as mock_logger:
            await self.middleware(event_context, "post")

            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_post_phase_handles_missing_event_name(self):
        """Test post phase handles missing event name."""
        test_error = ValueError("Test error")
        event_context = {"error": test_error}

        with patch("bot.middleware.error_handler.logger") as mock_logger:
            await self.middleware(event_context, "post")

            # Should log with "unknown" event name
            error_calls = mock_logger.error.call_args_list
            assert len(error_calls) == 2
            assert "Error in event unknown:" in str(error_calls[0])

    @pytest.mark.asyncio
    async def test_pre_phase_ignored(self):
        """Test that pre phase is ignored."""
        event_context = {"event_name": "test_event", "error": ValueError("Test error")}

        with patch("bot.middleware.error_handler.logger") as mock_logger:
            await self.middleware(event_context, "pre")

            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_other_phases_ignored(self):
        """Test that other phases are ignored."""
        event_context = {"event_name": "test_event", "error": ValueError("Test error")}

        with patch("bot.middleware.error_handler.logger") as mock_logger:
            await self.middleware(event_context, "unknown_phase")

            mock_logger.error.assert_not_called()

    def test_global_instance_exists(self):
        """Test that global error handler middleware instance exists."""
        assert error_handler_middleware is not None
        assert isinstance(error_handler_middleware, ErrorHandlerMiddleware)


class TestAnalyticsMiddleware:
    """Test AnalyticsMiddleware functionality."""

    def setup_method(self):
        """Setup test instance."""
        self.middleware = AnalyticsMiddleware()

    @pytest.mark.asyncio
    async def test_pre_phase_tracks_event_count(self):
        """Test that pre phase tracks event counts."""
        event_context = {"event_name": "test_event"}

        with patch("bot.middleware.analytics.logger") as mock_logger:
            await self.middleware(event_context, "pre")

            # Check event was counted
            assert self.middleware.event_counts["test_event"] == 1

            # Check logging
            mock_logger.info.assert_called_once_with("Analytics: test_event occurred (total: 1)")

    @pytest.mark.asyncio
    async def test_pre_phase_increments_existing_count(self):
        """Test that pre phase increments existing event counts."""
        event_context = {"event_name": "test_event"}

        # Set initial count
        self.middleware.event_counts["test_event"] = 5

        with patch("bot.middleware.analytics.logger") as mock_logger:
            await self.middleware(event_context, "pre")

            # Check count was incremented
            assert self.middleware.event_counts["test_event"] == 6

            # Check logging shows updated count
            mock_logger.info.assert_called_once_with("Analytics: test_event occurred (total: 6)")

    @pytest.mark.asyncio
    async def test_pre_phase_handles_missing_event_name(self):
        """Test pre phase handles missing event name gracefully."""
        event_context = {}

        with patch("bot.middleware.analytics.logger") as mock_logger:
            await self.middleware(event_context, "pre")

            # Should not crash and should not log
            mock_logger.info.assert_not_called()
            assert len(self.middleware.event_counts) == 0

    @pytest.mark.asyncio
    async def test_post_phase_ignored(self):
        """Test that post phase is ignored."""
        event_context = {"event_name": "test_event"}

        with patch("bot.middleware.analytics.logger") as mock_logger:
            await self.middleware(event_context, "post")

            mock_logger.info.assert_not_called()
            assert len(self.middleware.event_counts) == 0

    @pytest.mark.asyncio
    async def test_other_phases_ignored(self):
        """Test that other phases are ignored."""
        event_context = {"event_name": "test_event"}

        with patch("bot.middleware.analytics.logger") as mock_logger:
            await self.middleware(event_context, "unknown_phase")

            mock_logger.info.assert_not_called()
            assert len(self.middleware.event_counts) == 0

    def test_get_stats_returns_copy(self):
        """Test that get_stats returns a copy of event counts."""
        self.middleware.event_counts["event1"] = 10
        self.middleware.event_counts["event2"] = 5

        stats = self.middleware.get_stats()

        # Should return the same data
        assert stats == {"event1": 10, "event2": 5}

        # But should be a copy (modifying original shouldn't affect returned dict)
        self.middleware.event_counts["event1"] = 20
        assert stats["event1"] == 10  # Original copy unchanged

    def test_reset_stats_clears_counts(self):
        """Test that reset_stats clears event counts."""
        self.middleware.event_counts["event1"] = 10
        self.middleware.event_counts["event2"] = 5

        self.middleware.reset_stats()

        assert len(self.middleware.event_counts) == 0

    def test_global_instance_exists(self):
        """Test that global analytics middleware instance exists."""
        assert analytics_middleware is not None
        assert isinstance(analytics_middleware, AnalyticsMiddleware)


class TestMiddlewareIntegration:
    """Test middleware integration scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_middleware_can_be_chained(self):
        """Test that multiple middleware can process the same event."""
        logging_mid = LoggingMiddleware()
        analytics_mid = AnalyticsMiddleware()
        error_mid = ErrorHandlerMiddleware()

        event_context = {"event_name": "test_event"}

        # All should handle pre phase
        await logging_mid(event_context, "pre")
        await analytics_mid(event_context, "pre")
        await error_mid(event_context, "pre")

        # Check analytics tracked the event
        assert analytics_mid.event_counts["test_event"] == 1

        # Check logging tracked start time
        assert "test_event" in logging_mid.start_times

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test complete error handling workflow."""
        logging_mid = LoggingMiddleware()
        error_mid = ErrorHandlerMiddleware()

        event_context = {"event_name": "failing_event"}

        # Start event
        await logging_mid(event_context, "pre")

        # Simulate error occurring
        test_error = RuntimeError("Something went wrong")
        event_context["error"] = test_error

        # Process post phase
        with (
            patch("bot.middleware.logging.logger"),
            patch("bot.middleware.error_handler.logger") as error_logger,
        ):

            await logging_mid(event_context, "post")
            await error_mid(event_context, "post")

            # Error should be logged
            error_logger.error.assert_called()

    def test_all_middleware_imports_correctly(self):
        """Test that all middleware can be imported from the package."""
        from bot.middleware import (
            AnalyticsMiddleware,
            ErrorHandlerMiddleware,
            LoggingMiddleware,
        )

        # Should be able to create instances
        logging_mid = LoggingMiddleware()
        error_mid = ErrorHandlerMiddleware()
        analytics_mid = AnalyticsMiddleware()

        assert isinstance(logging_mid, LoggingMiddleware)
        assert isinstance(error_mid, ErrorHandlerMiddleware)
        assert isinstance(analytics_mid, AnalyticsMiddleware)
