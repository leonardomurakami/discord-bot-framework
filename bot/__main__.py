import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.core import DiscordBot
from config.settings import settings

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the Discord bot."""
    try:
        logger.info("Initializing Discord bot...")

        # Handle command line arguments
        if len(sys.argv) > 1 and sys.argv[1] == "--dev":
            # Force development mode
            import os
            os.environ["ENVIRONMENT"] = "development"

        # Create and run the bot
        bot = DiscordBot()

        # Bot ready to run

        # Run the bot
        bot.run()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()