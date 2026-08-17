from app.core.config import settings
from app.providers.research.base import ResearchProvider
from app.providers.research.mock import MockResearchProvider


def get_research_provider() -> ResearchProvider:
    """
    Factory function to return the configured ResearchProvider.
    Currently defaults to MockResearchProvider for development and testing.
    """
    provider_name = settings.RESEARCH_PROVIDER.lower()
    if provider_name == "mock":
        return MockResearchProvider()
    return MockResearchProvider()
