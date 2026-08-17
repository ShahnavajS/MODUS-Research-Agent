import logging
import sys
from app.core.config import settings


def setup_logging():
    level_str = getattr(settings, "LOG_LEVEL", "INFO")
    log_level = getattr(logging, level_str.upper() if isinstance(level_str, str) else "INFO", logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


logger = logging.getLogger("modus_research")
