import logging
import traceback
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware:
    def __init__(self) -> None:
        pass

    async def __call__(self, event_context: Dict[str, Any], phase: str) -> None:
        if phase == "post":
            # Check if any errors occurred during event processing
            if event_context.get("error"):
                error = event_context["error"]
                event_name = event_context.get("event_name", "unknown")

                # Log the error
                logger.error(f"Error in event {event_name}: {error}")
                logger.error(f"Traceback: {traceback.format_exception(type(error), error, error.__traceback__)}")

                # Here you could implement additional error handling:
                # - Send to error tracking service
                # - Notify administrators
                # - Save to database
                # etc.


# Global instance
error_handler_middleware = ErrorHandlerMiddleware()