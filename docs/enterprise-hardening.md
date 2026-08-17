# Enterprise Hardening, Security & Evaluation Architecture

## Overview

This document specifies the enterprise security, reliability, evaluation metrics, and observability safeguards built into the **MODUS Enterprise Research Intelligence Platform**.

---

## 1. Provider Isolation & Execution Transparency

The platform strictly isolates research pipeline orchestration from third-party AI models and web search engines through Abstract Base Classes (`AIProvider` and `ResearchProvider`).

Every `ResearchRun` explicitly tracks its execution mode:
- **`real`**: Executed via real web search (`duckduckgo_search`) and real Gemini AI API (`google-genai`).
- **`mock`**: Executed locally via deterministic mock providers (offline / testing mode).
- **`fallback`**: Executed with Gemini API in fallback mode due to unconfigured or invalid API keys.

The frontend receives `execution_mode` metadata and explicitly renders `REAL`, `MOCK`, or `FALLBACK` execution badges. Synthetic test data is never presented as genuine external research.

---

## 2. Prompt Versioning Registry

Prompts are versioned and stored in structured modules under `backend/app/prompts/`:
- `DECOMPOSITION_SYSTEM_PROMPT` (`v2`)
- `FINDING_EXTRACTION_SYSTEM_PROMPT` (`v2`)
- `CONTRADICTION_DETECTION_SYSTEM_PROMPT` (`v1`)
- `CONCLUSION_SYNTHESIS_SYSTEM_PROMPT` (`v2`)

Every completed `ResearchRun` records the prompt versions used in `run.metadata_json["prompt_versions"]`, providing complete auditability of AI behavior across model generations.

---

## 3. Web Security & SSRF Safeguards

The web acquisition layer implements Server-Side Request Forgery (SSRF) protection in `app.core.security.is_safe_external_url()`:

### Security Rules:
- **Allowed Schemes**: Only `http://` and `https://`. `file://`, `ftp://`, `gopher://` are rejected.
- **Blocked Hostnames**: `localhost`, `loopback`, `*.local`, `*.internal`, `metadata.google.internal`.
- **Blocked IP Networks**:
  - `127.0.0.0/8` (Loopback)
  - `10.0.0.0/8` (Private Class A)
  - `172.16.0.0/12` (Private Class B)
  - `192.168.0.0/16` (Private Class C)
  - `169.254.0.0/16` (Link-Local / AWS Metadata)
  - `::1/128` (IPv6 Loopback)
  - `fc00::/7` (IPv6 Unique Local)

### Execution Safeguards:
- **Max Document Size**: Enforces `MAX_DOCUMENT_SIZE_BYTES=500000` (500 KB) to prevent memory exhaust attacks.
- **Timeouts**: `CONTENT_EXTRACTION_TIMEOUT_SECONDS=8.0`.
- **No Code Execution**: Downloaded HTML is stripped of scripts, styles, and executable tags via `BeautifulSoup`. No arbitrary file URLs are accessed.

---

## 4. Deterministic Relevance Engine & Domain Quality

Source relevance is evaluated deterministically before content fetching:
- **Title Match (35%)**: Token overlap & Jaccard similarity.
- **Snippet Match (35%)**: Term frequency intersection.
- **Concept Match (20%)**: Important multi-word domain concept coverage.
- **Domain Quality (10%)**: Category classification weight.
  - Government (`.gov`): `0.95`
  - Academic (`.edu`): `0.92`
  - Research Publishers (`arxiv.org`, `ieee.org`, `nature.com`): `0.90`
  - Financial Institutions (`federalreserve.gov`, `bis.org`): `0.90`
  - Industry Analyst Reports (`mckinsey.com`, `gartner.com`): `0.88`
  - Reputable News (`reuters.com`, `bloomberg.com`, `wsj.com`): `0.85`
  - Enterprise Tech Blogs (`microsoft.com`, `google.com`): `0.82`
  - General Web: `0.70`
  - Dictionaries / Encyclopedias: `0.30`
  - Community Forums: `0.25`
  - Social Media: `0.15`

> **Note**: Domain quality is an auxiliary 10% weight. A high-quality domain with irrelevant content will still be rejected if title/snippet/concept scores are low.

---

## 5. Strict Failed-Source Evidence Exclusion

A web page with any of the following failure modes:
- HTTP 401 Unauthorized
- HTTP 403 Forbidden
- HTTP 404 Not Found
- HTTP 410 Gone
- HTTP 429 Rate Limited
- HTTP 5xx Server Error
- Connection failure / Timeout
- Empty response or unusable content (under 30 words)
- Error page / login wall pattern

**MUST NOT and DOES NOT enter finding extraction or evidence creation.**
The source is stored with `extraction_status = "failed"` and `lifecycle_state = "FETCH_FAILED"` for auditability, but produces zero evidence links.

---

## 6. Programmatic Evidence Validation

Every candidate finding and evidence link is validated in application code:
1. Source must have `FETCH_SUCCESS` and `EVIDENCE_ELIGIBLE`.
2. Evidence excerpt must be present verbatim in the stored source content.
3. Candidate statement must be a specific factual claim (generic templates like `"Enterprise research insight regarding..."` are rejected).
4. Invalid candidates are discarded; valid ones are linked to direct quotes via `Evidence` records.

---

## 7. Quality Metrics Framework

The `app.evaluation.metrics` module calculates research quality indicators stored in `run.metadata_json["quality_metrics"]`:

$$\text{Source Coverage} = \frac{\text{Successfully Fetched Sources}}{\text{Discovered Sources}}$$

$$\text{Evidence Coverage} = \frac{\text{Grounded Findings}}{\text{Total Findings}}$$

$$\text{Successful Fetch Rate} = \frac{\text{Fetch Success Sources}}{\text{Relevant Sources}}$$

$$\text{Evidence Eligibility Rate} = \frac{\text{Evidence Eligible Sources}}{\text{Fetch Success Sources}}$$

- `source_type_distribution` (Breakdown across government, academic, industry_report, news, general_web, etc.)
- `grounded_findings` vs `unsupported_findings`
- `contradiction_count`
- `conclusion_traceability` (Boolean verification that all conclusions map to member findings)
- `timing_breakdown` (Timing across decomposition, search, fetch, extraction, contradiction, synthesis)
