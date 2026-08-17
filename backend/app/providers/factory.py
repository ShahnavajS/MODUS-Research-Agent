import logging
from app.core.config import settings
from app.providers.base import AIProvider
from app.providers.gemini import GeminiAIProvider
from app.providers.mock import MockAIProvider
from app.providers.research.base import ResearchProvider
from app.providers.research.mock import MockResearchProvider
from app.providers.research.web import WebResearchProvider

logger = logging.getLogger(__name__)


def get_ai_provider() -> AIProvider:
    """Instantiate AI Provider based on system configuration."""
    provider_name = settings.AI_PROVIDER.lower().strip()
    if provider_name == "gemini":
        logger.info("Factory instantiating GeminiAIProvider")
        return GeminiAIProvider()
    
    logger.info("Factory instantiating MockAIProvider")
    return MockAIProvider()


def get_research_provider() -> ResearchProvider:
    """Instantiate Research Provider based on system configuration."""
    provider_name = settings.RESEARCH_PROVIDER.lower().strip()
    if provider_name == "web" or provider_name == "ddgs":
        logger.info("Factory instantiating WebResearchProvider")
        return WebResearchProvider()

    logger.info("Factory instantiating MockResearchProvider")
    return MockResearchProvider()
