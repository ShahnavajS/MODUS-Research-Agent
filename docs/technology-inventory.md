# Technology & Licence Inventory

This document inventory details all third-party libraries, frameworks, SDKs, and external services used in the **MODUS Enterprise Research Intelligence Platform**.

In accordance with MODUS AI Build Challenge requirements, all technologies chosen are open-source or offer free tiers, ensuring the platform can be executed and reproduced without paid software licenses.

| Technology / Package | Layer / Purpose | License | Free / Open-Source / Free-Tier Status | Requires External Service? | Fallback Strategy |
|---|---|---|---|---|---|
| **Python 3.10+** | Backend Runtime | PSF License (Open-Source) | 100% Free & Open-Source | No | None required |
| **FastAPI** | Async REST API Framework | MIT | 100% Free & Open-Source | No | None required |
| **Pydantic v2** | Data Validation & Schemas | MIT | 100% Free & Open-Source | No | None required |
| **SQLAlchemy 2.0** | Relational ORM & Async Engine | MIT | 100% Free & Open-Source | No | None required |
| **Alembic** | Database Migration Tool | MIT | 100% Free & Open-Source | No | None required |
| **SQLite / Aiosqlite** | Dev & Testing Database Engine | Public Domain / MIT | 100% Free & Open-Source | No | PostgreSQL |
| **google-genai** | Official Google Gemini Python SDK | Apache-2.0 | Free SDK (`gemini-2.5-flash` Free Tier) | Yes (Gemini API) | `MockAIProvider` (100% offline fallback) |
| **duckduckgo_search (DDGS)** | Web Search Acquisition Engine | MIT | Free Open-Source API (No API key needed) | Yes (DuckDuckGo Search) | `MockResearchProvider` (100% offline fallback) |
| **httpx** | Async HTTP Client | BSD-3-Clause | 100% Free & Open-Source | No | None required |
| **BeautifulSoup4** | HTML Cleaning & Plain Text Extraction | MIT | 100% Free & Open-Source | No | Fallback regex/title extraction |
| **React 18** | Frontend Web Library | MIT | 100% Free & Open-Source | No | None required |
| **Vite** | Frontend Build Tool & Dev Server | MIT | 100% Free & Open-Source | No | None required |
| **TypeScript** | Type-Safe JavaScript Superset | Apache-2.0 | 100% Free & Open-Source | No | None required |
| **Tailwind CSS v4** | Utility-First CSS Framework | MIT | 100% Free & Open-Source | No | Standard CSS |
| **Pytest** | Async Test Automation Framework | MIT | 100% Free & Open-Source | No | None required |

## Environment Configuration Modes

1. **Offline / Mock Mode (Default)**:
   - `AI_PROVIDER=mock`
   - `RESEARCH_PROVIDER=mock`
   - Zero external API keys or internet connection required. Runs 100% locally.

2. **Real Web Research & Gemini Mode**:
   - `AI_PROVIDER=gemini`
   - `RESEARCH_PROVIDER=web`
   - `GEMINI_API_KEY=<your_free_google_gemini_key>`
   - `GEMINI_MODEL=gemini-2.5-flash`
