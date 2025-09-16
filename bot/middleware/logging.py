import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def __init__(self) -> None:
        self.start_times: dict[str, float] = {}

    async def __call__(self, event_context: dict[str, Any], phase: str) -> None:
        event_name = event_context.get("event_name")

        if phase == "pre":
            # Log event start
            self.start_times[event_name] = time.time()
            logger.debug(f"Event started: {event_name}")

        elif phase == "post":
            # Log event completion
            start_time = self.start_times.pop(event_name, None)
            if start_time:
                duration = time.time() - start_time
                logger.debug(f"Event completed: {event_name} (took {duration:.3f}s)")
            else:
                logger.debug(f"Event completed: {event_name}")


# Global instance
logging_middleware = LoggingMiddleware()
