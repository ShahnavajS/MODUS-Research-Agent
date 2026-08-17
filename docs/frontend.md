# Frontend Architecture & Workspace UI Documentation

## Overview

The frontend layer of the **Enterprise Research Intelligence Platform** is built with React 18, Vite, TypeScript, and Tailwind CSS v4. It translates raw backend REST API responses into a high-end, responsive enterprise research workspace with full evidence traceability.

```
┌─────────────────────────────────────────────────────────────┐
│                       MainLayout                           │
│     (Header Navigation + Health Indicator + App Router)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐
│  Dashboard  │         │  Workspace  │         │ Audit Log   │
│ (Workspaces)│         │ (Launcher)  │         │ (History)   │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
┌──────▼───────────────────────▼───────────────────────▼──────┐
│                  Research Results View                      │
│ (Conclusion → Findings → Evidence Excerpts → Sources)       │
└─────────────────────────────────────────────────────────────┘
```

## Core Views & User Workflows

1. **Dashboard & Workspaces (`DashboardPage.tsx`)**:
   - Workspace grid listing all research projects with status badges (`active`, `completed`, `draft`).
   - Live search input filtering projects by name, research topic, or industry.
   - Create Workspace modal (`CreateProjectModal.tsx`).

2. **Project Detail View (`ProjectDetailPage.tsx`)**:
   - Detailed workspace header displaying topic and industry metadata.
   - Form to submit new research questions under the active project.
   - List of research questions and associated execution runs.
   - One-click **"Trigger & Execute Pipeline"** action button.

3. **Interactive Pipeline Launcher (`ResearchWorkspacePage.tsx`)**:
   - Dynamic prompt launcher for entering completely new research questions.
   - Step-by-step pipeline execution monitor animating stage progress (`Decomposing`, `Discovering Sources`, `Extracting Evidence`, `Synthesizing Conclusion`).

4. **Explainability & Research Results (`ResearchResultsPage.tsx`)**:
   - **Metrics Summary Bar**: Displays counts for sub-questions, sources, findings, evidence excerpts, contradictions, and conclusions.
   - **Synthesized Conclusion Panel (`ConclusionPanel.tsx`)**: Displays high-level conclusions with a confidence percentage meter and member findings references.
   - **Traceable Findings List (`FindingCard.tsx`)**: Atomic findings with type (`fact`, `risk`, `trend`), confidence, importance, and expandable evidence excerpts linking to source URLs and credibility scores.
   - **Contradiction Audit (`ContradictionList.tsx`)**: Highlights conflicting evidence between findings with severity ratings (`low`, `medium`, `high`) and resolution notes.
   - **Acquired Sources (`SourceList.tsx`)**: Source list with publisher details, publication date, credibility score, and expandable raw text modal.

5. **Traceability Audit History (`ResearchHistoryPage.tsx`)**:
   - Chronological log of all executed research runs across all projects.
   - Real-time search query filtering by question string or workspace topic.
   - Status badges and entity metric counters.

## Complete Explainability Chain

The UI strictly renders backend data to visualize the explainability chain:

$$\text{Conclusion} \xrightarrow{\text{many-to-many}} \text{Finding} \xrightarrow{\text{foreign key}} \text{Evidence Excerpt} \xrightarrow{\text{foreign key}} \text{Source Content \& URL}$$

## Component Hierarchy

```
frontend/src/
├── components/
│   ├── common/
│   │   ├── Badge.tsx
│   │   ├── LoadingSkeleton.tsx
│   │   ├── MetricCard.tsx
│   │   └── Modal.tsx
│   └── research/
│       ├── ConclusionPanel.tsx
│       ├── ContradictionList.tsx
│       ├── CreateProjectModal.tsx
│       ├── FindingCard.tsx
│       ├── SourceList.tsx
│       └── HealthIndicator.tsx
├── layouts/
│   └── MainLayout.tsx
├── pages/
│   ├── DashboardPage.tsx
│   ├── ProjectDetailPage.tsx
│   ├── ResearchHistoryPage.tsx
│   ├── ResearchResultsPage.tsx
│   └── ResearchWorkspacePage.tsx
├── services/
│   └── api.ts
└── types/
    └── index.ts
```

## Live Demonstration Flow (MODUS Validation)

1. Open application at `http://localhost:5173`.
2. Select or create a Research Workspace (e.g. *"AI Transformation in Retail"*).
3. Navigate to **Research Launcher** tab.
4. Enter a completely new research question (e.g. *"How is AI transforming retail store operations and inventory management?"*).
5. Click **Execute Research Pipeline**.
6. Observe the real-time stage progress monitor.
7. System automatically redirects to **Research Results View**.
8. Inspect the **Synthesized Conclusion** and confidence meter.
9. Expand **Findings & Traceable Evidence Excerpts**.
10. Click **Inspect Source URL** to view external source metadata and full extracted document text.
11. Check **Contradictions** tab to inspect conflicting evidence.
12. Navigate to **Audit History** to see the persistent chronological run history.
