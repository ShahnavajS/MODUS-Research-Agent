from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResearchSearchResult(BaseModel):
    title: str = Field(..., description="Title of the discovered search result")
    url: str = Field(..., description="URL of the source document")
    publisher: Optional[str] = Field(None, description="Publishing organization")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")
    source_type: str = Field("web", description="Type of source e.g. report, article, paper")
    snippet: str = Field(..., description="Short summary snippet from search index")
    credibility_score: float = Field(0.8, description="Estimated credibility score (0.0 - 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary provider metadata")


class ResearchDocument(BaseModel):
    url: str = Field(..., description="URL of the document")
    title: str = Field(..., description="Title of the document")
    content: str = Field(..., description="Extracted plain text or markdown content")
    content_hash: Optional[str] = Field(None, description="Hash of the document content")
    word_count: int = Field(..., description="Word count of the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary document metadata")


class ResearchProvider(ABC):
    """
    Abstract Base Class for external search and web acquisition providers.
    Decouples research pipeline logic from specific search APIs (Bing, Google, Brave, Tavily, etc.).
    """

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[ResearchSearchResult]:
        """Search external sources given a query."""
        pass

    @abstractmethod
    async def fetch_content(self, url: str) -> ResearchDocument:
        """Fetch and extract full text content from a source URL."""
        pass
