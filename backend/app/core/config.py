from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite+aiosqlite:///./research_platform.db"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173", "*"]

    # Provider Settings
    AI_PROVIDER: str = "mock"  # "mock" | "gemini"
    RESEARCH_PROVIDER: str = "mock"  # "mock" | "web"

    # Real Gemini Provider Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ─── Research Pipeline Configuration ─────────────────────────────────
    # Question decomposition
    MAX_SUBQUESTIONS: int = 4

    # Search
    MAX_SEARCH_QUERIES_PER_SUBQUESTION: int = 2
    RESEARCH_RESULTS_PER_QUERY: int = 5
    MAX_CONCURRENT_SEARCHES: int = 4

    # Source selection (rank-and-select-top-N)
    MAX_SELECTED_SOURCES: int = 12
    MAX_SOURCES_PER_DOMAIN: int = 2

    # Fetch
    MAX_CONCURRENT_FETCHES: int = 5
    CONTENT_EXTRACTION_TIMEOUT_SECONDS: float = 8.0
    MAX_DOCUMENT_SIZE_BYTES: int = 500_000
    MIN_CONTENT_WORD_COUNT: int = 30

    # Finding extraction
    EXTRACTION_BATCH_SIZE: int = 3
    MAX_CONCURRENT_EXTRACTIONS: int = 3
    MAX_FINDINGS_PER_SOURCE: int = 5

    # Deduplication & Caps
    DEDUP_SIMILARITY_THRESHOLD: float = 0.55
    MAX_FINDINGS_PER_RUN: int = 40

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> str:
        if isinstance(v, str):
            # Render / Neon often provide postgres:// or postgresql://
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v or "sqlite+aiosqlite:///./research_platform.db"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173", "*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
