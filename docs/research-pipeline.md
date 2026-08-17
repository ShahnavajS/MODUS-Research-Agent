# Research Intelligence Pipeline Documentation

## Pipeline Overview

The **Research Intelligence Pipeline** orchestrates structured, multi-stage enterprise research. The system avoids simple ungrounded chatbot responses by strictly deriving all conclusions from acquired, validated external source content.

```
User Research Question
       │
       ▼
Research Run Initialization
       │
       ▼
Stage 1: Question Decomposition (Gemini Structured Output / Focused Sub-Inquiries)
       │
       ▼
Stage 2: Dynamic Query Generation & Multi-Query Search (DuckDuckGo DDGS)
       │
       ▼
Stage 3: Deterministic Source Relevance & Domain Classification Filtering
       │  ├─ REJECTED_IRRELEVANT (< MIN_SOURCE_RELEVANCE_SCORE) -> Discarded before fetch
       │  └─ RELEVANT (>= MIN_SOURCE_RELEVANCE_SCORE) -> Proceed to fetch
       │
       ▼
Stage 4: Bounded Concurrent Content Fetching (asyncio.gather + Semaphore)
       │  ├─ FETCH_FAILED (401/403/404/5xx/timeout/empty) -> NOT_ELIGIBLE_FOR_EVIDENCE
       │  └─ FETCH_SUCCESS (HTTP 200 + validated text) -> EVIDENCE_ELIGIBLE
       │
       ▼
Stage 5: Grounded Finding Extraction (AI Provider - Eligible Sources ONLY)
       │  ├─ Verbatim Text Excerpt Matching
       │  ├─ Generic Template Rejection Filter
       │  └─ Programmatic Evidence Validation
       │
       ▼
Stage 6: Contradiction & Conflict Detection (Cross-Finding Analysis)
       │
       ▼
Stage 7: Grounded Conclusion Synthesis & Insufficiency Disclosure
       │
       ▼
Persist Knowledge Graph, Telemetry & Quality Metrics
       │
       ▼
Traceable UI Results & Programmatic Provenance Graph (`/traceability`)
```

---

## Explicit Source Lifecycle

The pipeline manages each candidate source through a strict, transparent lifecycle:

```
DISCOVERED
    │
    ▼
RELEVANCE_EVALUATED
    │
    ├──▶ REJECTED_IRRELEVANT (below MIN_SOURCE_RELEVANCE_SCORE) [Discarded]
    ▼
RELEVANT
    │
    ▼
FETCH_ATTEMPTED
    │
    ├──▶ FETCH_FAILED (HTTP 401/403/404/410/429/5xx, timeout, empty) [NOT_ELIGIBLE]
    ▼
FETCH_SUCCESS
    │
    ▼
CONTENT_VALIDATED (min word count, non-error page)
    │
    ▼
EVIDENCE_ELIGIBLE (passed to AI for finding extraction & evidence linking)
```

---

## Detailed Pipeline Stages

### 1. Question Decomposition
- Decomposes original question into 3-5 focused sub-inquiries using Gemini structured JSON schema validation.
- Sub-questions cover distinct dimensions (deployment patterns, ROI/benefits, risks, governance/regulation).
- Bounded by `MAX_SUBQUESTIONS` (default: 5).

### 2. Dynamic Query Generation & Search
- Generates 2-3 focused search queries per sub-question by extracting key concepts and stripping conversational prefixes.
- Searches via `WebResearchProvider` (`duckduckgo_search.DDGS()`).
- Normalizes URLs (stripping tracking parameters, fragments, trailing slashes).
- Detects near-duplicates using domain matching and title similarity.

### 3. Deterministic Source Relevance Engine
- Reusable evaluator in `app.evaluation.relevance`.
- Scores sources based on 4 explainable components:
  - **Title Match (35%)**: Token overlap & Jaccard similarity.
  - **Snippet Match (35%)**: Term frequency intersection.
  - **Concept Match (20%)**: Key multi-word concept coverage.
  - **Domain Quality (10%)**: Category classification weight.
- Formula: $\text{relevance\_score} = 0.35 \times \text{title} + 0.35 \times \text{snippet} + 0.20 \times \text{concept} + 0.10 \times \text{domain}$
- Sources below `MIN_SOURCE_RELEVANCE_SCORE` (default: 0.35) are marked `REJECTED_IRRELEVANT` and never fetched.

### 4. Bounded Concurrent Content Acquisition & Strict Fetch Contract
- Fetches relevant pages in parallel using `asyncio.gather` with `asyncio.Semaphore(MAX_CONCURRENT_FETCHES)` (default: 5).
- Configurable timeout: `CONTENT_EXTRACTION_TIMEOUT_SECONDS=8.0`.
- Validates extracted text: rejects error pages, login walls, and content under `MIN_CONTENT_WORD_COUNT` (default: 30).
- **Strict Failed Source Contract**:
  - Failed pages (401, 403, 404, 410, 429, 5xx, timeout, empty text) are marked `FETCH_FAILED` and `NOT_ELIGIBLE_FOR_EVIDENCE`.
  - Stored in database for auditability with failure status, but **NEVER passed to AI models** or used for evidence.

### 5. Finding Extraction & Programmatic Evidence Validation
- Pass **ONLY** `EVIDENCE_ELIGIBLE` sources to AI finding extraction.
- The prompt instructs AI to extract findings strictly from supplied text with verbatim excerpts and forbids prior knowledge or generic template findings.
- **Programmatic Validation**:
  - Source must have `FETCH_SUCCESS` and `EVIDENCE_ELIGIBLE`.
  - Excerpt must exist verbatim in the source content text.
  - Generic template patterns are automatically rejected.
  - Validated findings are linked to direct quotes via `Evidence` records.

### 6. Contradiction Detection
- Cross-audits validated findings for genuine material contradictions with severity ratings (`low`, `medium`, `high`).

### 7. Grounded Conclusion Synthesis & Insufficiency Policy
- Synthesizes executive conclusions directly answering the research question.
- Covers: main answer, deployment patterns, metrics/benefits, risks, governance, and evidence limitations.
- **Evidence Insufficiency Policy**: If available evidence is sparse, the conclusion explicitly states evidence gaps rather than hallucinating facts.

---

## Research Quality Telemetry & Provenance

Execution metadata recorded in `run.metadata_json`:
- `discovered_sources_count`
- `relevant_sources_count`
- `rejected_irrelevant_count`
- `fetch_success_count`
- `failed_sources_count`
- `evidence_eligible_count`
- `source_type_distribution` (`government`, `academic`, `financial_institution`, `enterprise`, `industry_report`, `news`, `general_web`, etc.)
- `grounded_findings_count` & `unsupported_findings_count`
- `evidence_coverage` & `source_coverage`
- `timing_breakdown` (`search_seconds`, `fetch_seconds`, `extraction_seconds`, `validation_seconds`, `synthesis_seconds`, `total_seconds`)

Accessible programmatically via `GET /api/v1/runs/{run_id}/traceability`.
