# Enterprise Research Intelligence Platform

An enterprise-grade, traceable research intelligence agent capable of conducting structured enterprise research at scale.

## Overview

The Enterprise Research Intelligence Platform is a layered, modular monolith designed for automated multi-source research, source storage, finding extraction, evidence linkage, contradiction detection, and traceable conclusion generation.

## Target Architecture

```
Frontend (React + Vite + TypeScript + Tailwind CSS - Auralis Design System)
    ↓ (HTTP / REST API)
API / Application Layer (FastAPI + Pydantic v2)
    ↓
Research Orchestration Layer (Services & Pipeline Stages)
    ↓
AI & Research Provider Abstraction Layers (AIProvider & ResearchProvider)
    ├── Real Providers: GeminiAIProvider (google-genai) & WebResearchProvider (ddgs + httpx)
    └── Mock Providers: MockAIProvider & MockResearchProvider (Offline / Testing)
    ↓
Knowledge / Data Layer (SQLAlchemy ORM + Alembic + PostgreSQL / SQLite)
```

## Data Model & Pipeline

```
ResearchProject
  └── ResearchQuestion
        └── ResearchRun
              ├── ResearchSubQuestion
              ├── ResearchSource
              │     └── SourceContent
              ├── Finding
              │     └── Evidence ──> ResearchSource / SourceContent
              ├── Contradiction (Finding A ↔ Finding B)
              └── Conclusion ──> Findings (Many-to-Many)
```

## Technology Stack

- **Backend**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0, AsyncPG / Aiosqlite, Alembic, `google-genai`, `duckduckgo_search`, `httpx`, `beautifulsoup4`, Pytest
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS v4 (Auralis visual design system)
- **Database**: PostgreSQL (Production) / SQLite (Dev & Testing)
- **AI & Research Abstractions**: Provider-agnostic Abstract Base Classes (`AIProvider`, `ResearchProvider`)

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL (optional; SQLite fallback included)

### Environment Modes

#### 1. Offline / Testing Mode (Default - No API Key Needed)
```bash
AI_PROVIDER=mock
RESEARCH_PROVIDER=mock
```

#### 2. Real Web Research & Gemini Mode
```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=<your_free_google_gemini_api_key>
GEMINI_MODEL=gemini-2.5-flash
RESEARCH_PROVIDER=web
RESEARCH_RESULTS_PER_QUERY=5
MAX_SUBQUESTIONS=5
MAX_SEARCH_QUERIES_PER_SUBQUESTION=2
```

### Backend Setup

1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run database migrations and seed sample data:
   ```bash
   python -m alembic upgrade head
   python -m app.seed
   ```
4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Interactive API docs: `http://localhost:8000/docs`

### Frontend Setup

1. Navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependencies & start Vite dev server:
   ```bash
   npm install
   npm run dev
   ```
   Access web application at `http://localhost:5173`

### Running Tests

- **Backend Unit & Integration Tests**:
  ```bash
  cd backend
  python -m pytest -v
  ```
- **Frontend Production Build**:
  ```bash
  cd frontend
  npm run build
  ```

## Current Implementation Status

- [x] **Step 1**: Core application foundation, project structure, FastAPI shell, health endpoint, provider abstraction interface.
- [x] **Step 2**: Core relational domain schema (Project, Question, Run, Source, SourceContent, Finding, Evidence, Contradiction, Conclusion), Alembic migrations, CRUD API endpoints, Pydantic schemas, Repository pattern, async SQLAlchemy, dev seed script.
- [x] **Step 3**: Multi-stage Research Intelligence Pipeline (`ResearchPipelineService`), `ResearchSubQuestion` model & migration 002, URL deduplication, provider abstractions, mock providers, execution API `POST /api/v1/runs/{id}/execute`, and pytest suite.
- [x] **Step 4**: Complete frontend workspace redesign adhering to the Auralis visual design language (Burned Amber `#EA580C`, dark obsidian `#191C21`, Geist + JetBrains Mono typography, evidence traceability UI, and health indicator API integration).
- [x] **Step 5**: Real Research & AI Pipeline implementation (`GeminiAIProvider` using `google-genai` SDK with Pydantic structured output, `WebResearchProvider` using `duckduckgo_search` + `httpx` HTML text extraction, URL normalization, evidence validation, run traceability endpoint `GET /api/v1/runs/{id}/traceability`, technology inventory, and 18 passing backend tests).
