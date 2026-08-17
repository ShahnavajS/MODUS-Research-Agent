# MODUS Enterprise Research Agent — Technical Demonstration Script

A 10–15 minute structured technical demonstration script for the **MODUS Enterprise AI Build Challenge**.

---

## Timeline & Demonstration Flow

### 00:00 – 01:30 | Introduction & Challenge Problem
- **Speaker**: "Welcome. Enterprise decision-makers cannot rely on ungrounded AI chatbots that produce hallucinatory prose without citations. Today we demonstrate the MODUS Enterprise Research Agent—an enterprise-grade research platform that conducts structured multi-source research at scale with 100% evidence traceability."
- **Visual**: Show application home screen at `http://localhost:5173`. Point out `API: ONLINE (sqlite)` health status badge and Auralis visual design system.

### 01:30 – 03:00 | Architecture & Provider Isolation Overview
- **Speaker**: "The system is built as a layered modular monolith in Python FastAPI and React TypeScript. AI intelligence and web search engines are completely decoupled behind abstract interfaces (`AIProvider` and `ResearchProvider`). We support real Gemini AI (`google-genai`), real DuckDuckGo web search (`ddgs`), and 100% offline mock execution."
- **Visual**: Show architecture diagram in [`docs/research-pipeline.md`](file:///c:/Users/sanus/Desktop/MODUS%20AI/docs/research-pipeline.md) or [`docs/technology-inventory.md`](file:///c:/Users/sanus/Desktop/MODUS%20AI/docs/technology-inventory.md).

### 03:00 – 05:00 | Workspace & Research Execution
- **Speaker**: "Let's create a new enterprise research workspace and launch a real research inquiry."
- **Action**: Click **+ Create Workspace**, name it *"Financial AI Governance"*, research topic *"Generative AI in Banking"*.
- **Action**: Navigate to **Research Launcher**. Select the new workspace.
- **Action**: Enter research question:
  `"How is generative AI changing customer service operations in the banking industry?"`
- **Action**: Click **RUN RESEARCH PIPELINE 🚀**.
- **Visual**: Highlight the real-time stage progress monitor animating through `01 QUESTION`, `02 DECOMPOSITION`, `03 SOURCE DISCOVERY`, `04 CONTENT ANALYSIS`, `05 FINDINGS`, `06 EVIDENCE`, `07 CONTRADICTIONS`, `08 SYNTHESIS`.

### 05:00 – 08:00 | Results & Executive Synthesis
- **Speaker**: "The pipeline has completed. Notice the execution metadata bar: mode `REAL`, AI model `gemini-2.5-flash`, search engine `WebResearchProvider`, execution time `6.52s`."
- **Visual**: Inspect **Executive Conclusion** card. Point out the confidence meter (e.g. 88%) and supporting finding count.

### 08:00 – 11:00 | Evidence Traceability Drill-Down
- **Speaker**: "Now let's examine the core requirement: explainability and evidence traceability."
- **Action**: Click **Findings & Evidence** tab. Select Finding #1.
- **Action**: Expand **Traceable Supporting Evidence**. Highlight the direct verbatim text excerpt extracted from HTML.
- **Action**: Click **Inspect Source Document ↗**. Show publisher metadata, domain credibility score (e.g. 0.95 for government/academic), and raw extracted text content in the source document reader modal.
- **Speaker**: "Every conclusion statement maps to atomic findings, which map to exact source text excerpts and verified URLs."

### 11:00 – 12:30 | Contradiction Audit & Security Safeguards
- **Speaker**: "When sources disagree, our system does not average or hide the conflict. It preserves analytical tension."
- **Action**: Click **Contradictions** tab. Show Claim A vs Claim B conflict audit card, severity tag, and resolution status.
- **Speaker**: "Our web acquisition layer incorporates SSRF security safeguards, blocking internal IPs, loopbacks, and non-HTTP schemes."

### 12:30 – 14:00 | Audit History & Programmatic Provenance API
- **Speaker**: "All execution runs are recorded in audit history."
- **Action**: Click **Audit History** tab. Show chronological run log.
- **Action**: Demonstrate programmatic provenance API: open `http://localhost:8000/api/v1/runs/{run_id}/traceability` or show REST docs.

### 14:00 – 15:00 | Summary & Future Scalability
- **Speaker**: "In summary, the MODUS Enterprise Research Agent demonstrates genuine enterprise AI engineering: reproducible open-source stack, SSRF security, Pydantic structured AI outputs, evidence validation, and complete provenance traceability. Thank you."
