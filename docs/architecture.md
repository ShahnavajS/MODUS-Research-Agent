# System Architecture

## Architecture Overview

The **Enterprise Research Intelligence Platform** is built using a clean, layered modular monolith architecture. Business logic is strictly isolated from presentation, data access, search engines, and AI providers.

```
┌─────────────────────────────────────────────────────────────┐
│             Frontend (React + TS + Auralis UI)              │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API (JSON)
┌──────────────────────────────▼──────────────────────────────┐
│                    API Layer (FastAPI Routers)              │
└──────────────────────────────┬──────────────────────────────┘
                               │ DTOs / Schemas
┌──────────────────────────────▼──────────────────────────────┐
│                    Service / Business Layer                 │
│              (ResearchPipelineService & Domain)             │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼──────────────┐┌──────────────▼──────────────┐
│      Repository Layer       ││     AI & Research Provider   │
│  (SQLAlchemy Data Access)   ││      Abstraction Layers     │
└──────────────┬──────────────┘└──────────────┬──────────────┘
               │                              │
┌──────────────▼──────────────┐┌──────────────▼──────────────┐
│  Data Layer (PostgreSQL/    ││    External LLM & Search    │
│         SQLite DB)          ││  (Gemini 2.5, DDGS, Mock)    │
└─────────────────────────────┘└─────────────────────────────┘
```

## Layer Descriptions

1. **Frontend Layer**: Built with React 18, Vite, TypeScript, and Tailwind CSS (Auralis visual design system). Provides workspace management, research question submission, pipeline execution status monitoring, evidence inspection, and traceability graphs.
2. **API Layer**: FastAPI routers handle request routing, validation, error mapping, and response formatting (`/api/v1/projects`, `/api/v1/questions`, `/api/v1/runs/{id}/execute`, `/api/v1/runs/{id}/traceability`).
3. **Research Orchestration Layer (`ResearchPipelineService`)**: Manages the multi-stage research workflow:
   - Question Decomposition (`ResearchSubQuestions`)
   - Source Discovery & URL Normalization
   - SSRF-Guarded HTML Content Acquisition & Cleaning (`httpx` + `BeautifulSoup`)
   - Finding Extraction & Strict Evidence Validation
   - Contradiction Detection & Conflict Auditing
   - Executive Conclusion Generation & Association
   - Research Quality Metrics Calculation (`source_coverage`, `evidence_coverage`, `traceability`)
4. **Repository Layer**: Encapsulates database queries using SQLAlchemy ORM (async). Provides clean interfaces for data access without leaking database mechanics.
5. **AI & Research Provider Abstraction Layer**: Abstract Base Classes (`AIProvider` and `ResearchProvider`) isolate LLM prompting, search indexing, and web fetching SDKs from core research business logic.
   - Real Providers: `GeminiAIProvider` (Google `google-genai` SDK with Pydantic structured output) & `WebResearchProvider` (`duckduckgo_search` DDGS + SSRF-guarded HTTP client).
   - Mock Providers: `MockAIProvider` & `MockResearchProvider` (100% offline testing).
6. **Data Layer**: Relational database persistence using PostgreSQL (or SQLite for dev/test). Evolution is managed via Alembic migrations (`001_initial_schema`, `002_add_research_sub_questions`).
