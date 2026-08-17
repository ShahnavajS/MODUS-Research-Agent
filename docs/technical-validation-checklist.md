# Technical Validation Checklist & Architectural Justifications

This document provides explicit answers and technical evidence for evaluation during the **MODUS Enterprise AI Build Challenge**.

---

## 1. Architecture

### Why Modular Monolith?
- **CURRENT**: A layered modular monolith (`backend/app/` with `api`, `services`, `repositories`, `providers`, `models`, `evaluation`) minimizes operational overhead, avoids distributed network latency, simplifies local reproduction, and eliminates complex service mesh orchestration during rapid evaluation.
- **FUTURE**: Service boundaries (such as `ResearchPipelineService` and `WebResearchProvider`) are decoupled via interfaces and can be extracted into async Celery / Redis worker queues or worker microservices if scale requires.

### Why PostgreSQL / SQLite SQLAlchemy ORM?
- **CURRENT**: Relational persistence is required to maintain relational integrity across Projects, Questions, Runs, Sources, SourceContents, Findings, Evidence, Contradictions, and Conclusions. SQLite with `aiosqlite` allows 100% zero-dependency offline test execution; PostgreSQL with `asyncpg` powers production workloads.
- **FUTURE**: Partitioning historical `ResearchRun` and `SourceContent` tables by timestamp or organization ID.

### Why Provider Abstraction?
- **CURRENT**: Abstract base classes (`AIProvider` and `ResearchProvider`) decouple business orchestration from third-party vendor APIs. Switching from `GeminiAIProvider` to `MockAIProvider` requires changing a single environment variable (`AI_PROVIDER=mock`).
- **FUTURE**: Adding OpenAI, Anthropic, or local open-source LLMs (Ollama / vLLM) by implementing the `AIProvider` interface.

### Why Structured AI Output?
- **CURRENT**: Eliminates fragile regular expression string parsing. Gemini's native Pydantic schema validation (`response_mime_type="application/json"`, `response_schema=PydanticModel`) guarantees that all model outputs conform to expected typed schemas.

---

## 2. Source Lifecycle & Retrieval Relevance

### How are Irrelevant Sources Filtered Out?
- **CURRENT**: Deterministic Source Relevance Engine (`app.evaluation.relevance`).
  - Evaluates every candidate search result using 4 explainable signals:
    - **Title Match (35%)**: Token overlap & Jaccard similarity.
    - **Snippet Match (35%)**: Term frequency intersection.
    - **Concept Match (20%)**: Important domain concept coverage.
    - **Domain Quality (10%)**: Category classification weight.
  - Threshold: Sources scoring below `MIN_SOURCE_RELEVANCE_SCORE` (0.35) are marked `REJECTED_IRRELEVANT` and never fetched, saving bandwidth and network time.

### How are Noise Domains Handled?
- **CURRENT**: Domains are classified into structured categories (`government`, `academic`, `research`, `financial_institution`, `industry_report`, `news`, `enterprise`, `general_web`, `reference_dictionary`, `community_forum`, `social_media`). Non-research categories receive lower domain weights, causing them to fail the relevance threshold unless content is exceptionally relevant.

---

## 3. Strict Failed-Source Protection & Evidence Grounding

### What happens if a target website returns 401 / 403 / 404 / 5xx / timeout?
- **CURRENT**:
  1. The provider marks the source with `fetch_status = "FETCH_FAILED"` and `extraction_status = "failed"`.
  2. The source is marked `NOT_ELIGIBLE_FOR_EVIDENCE`.
  3. No synthetic or fallback content is created.
  4. The source is retained in the database for auditability and transparency, but **is NEVER passed to the AI for finding extraction** and **NEVER used to create evidence**.

### How is Evidence Programmatically Validated?
- **CURRENT**: Application code (not the LLM) enforces:
  1. Source must have `FETCH_SUCCESS` and `EVIDENCE_ELIGIBLE`.
  2. Source content must exist and contain >= 30 words of meaningful text (non-error page).
  3. Evidence excerpt must be present verbatim in the stored source content.
  4. Finding claim must be specific and grounded in evidence. Generic template patterns (`"Enterprise research insight regarding..."`) are rejected.

### How is Evidence Insufficiency Handled?
- **CURRENT**: If available evidence is sparse or insufficient:
  - Fewer findings are produced with appropriate confidence ratings.
  - The conclusion explicitly states evidence limitations and gaps rather than hallucinating facts.
  - Treated as a successful, safe, grounded outcome rather than a pipeline crash.

---

## 4. Scalability & Performance

### How is Runtime Optimized (<90 Seconds)?
- **CURRENT**:
  1. Irrelevant sources are filtered out *before* HTTP content fetching.
  2. Content fetching is parallelized using `asyncio.gather` with a bounded semaphore (`MAX_CONCURRENT_FETCHES=5`).
  3. Search queries are stripped of conversational prefixes to target core keywords directly.
  4. Bounded HTTP timeouts (`CONTENT_EXTRACTION_TIMEOUT_SECONDS=8.0`).
- **FUTURE**: Database read replicas, Redis caching for source document text, and vector database indexing (pgvector / Qdrant) for semantic search over cached sources.

---

## 5. Explainability & Provenance

### How do you trace a conclusion?
- **CURRENT**: Programmatically via `GET /api/v1/runs/{id}/traceability` or visually in the UI.
  $$\text{Conclusion} \longrightarrow \text{Finding} \longrightarrow \text{Evidence Excerpt} \longrightarrow \text{Source URL} \longrightarrow \text{Source Content}$$

### How do you inspect supporting evidence?
- **CURRENT**: Expandable evidence cards in the UI displaying verbatim text excerpts, relevance scores, credibility ratings, and source document URLs.
