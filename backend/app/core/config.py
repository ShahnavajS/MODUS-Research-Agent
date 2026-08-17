from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./research_platform.db"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # Provider Settings
    AI_PROVIDER: str = "mock"  # "mock" | "gemini"
    RESEARCH_PROVIDER: str = "mock"  # "mock" | "web"
    
    # Real Gemini Provider Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Research Query & Extraction Limits
    RESEARCH_RESULTS_PER_QUERY: int = 5
    MAX_SUBQUESTIONS: int = 5
    MAX_SEARCH_QUERIES_PER_SUBQUESTION: int = 2
    CONTENT_EXTRACTION_TIMEOUT_SECONDS: float = 8.0
    MAX_DOCUMENT_SIZE_BYTES: int = 500_000

    # Source Relevance & Filtering
    MIN_SOURCE_RELEVANCE_SCORE: float = 0.35
    MIN_CONTENT_WORD_COUNT: int = 30

    # Performance & Concurrency
    MAX_CONCURRENT_SEARCHES: int = 4
    MAX_CONCURRENT_FETCHES: int = 5
    MAX_CONCURRENT_EXTRACTION_BATCHES: int = 3
    MAX_SOURCES_PER_EXTRACTION_BATCH: int = 3

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


settings = Settings()
