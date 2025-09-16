import logging
from typing import Any

logger = logging.getLogger(__name__)


class AnalyticsMiddleware:
    def __init__(self) -> None:
        self.event_counts: dict[str, int] = {}

    async def __call__(self, event_context: dict[str, Any], phase: str) -> None:
        if phase == "pre":
            event_name = event_context.get("event_name")
            if event_name:
                # Track event occurrence
                self.event_counts[event_name] = self.event_counts.get(event_name, 0) + 1

                # Log analytics data (could be sent to external service)
                logger.info(
                    f"Analytics: {event_name} occurred (total: {self.event_counts[event_name]})"
                )

                # Here you could implement:
                # - Send metrics to monitoring services
                # - Store analytics in database
                # - Track user behavior patterns
                # etc.

    def get_stats(self) -> dict[str, int]:
        return self.event_counts.copy()

    def reset_stats(self) -> None:
        self.event_counts.clear()


# Global instance
analytics_middleware = AnalyticsMiddleware()
