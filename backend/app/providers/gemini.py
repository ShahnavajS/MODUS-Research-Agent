"""
Production Gemini AI Intelligence Provider.

Uses Google's official `google-genai` SDK with structured output (Pydantic schemas)
to guarantee validated model output for:
  - Question decomposition
  - Finding extraction (batched with strict source attribution and per-source cap)
  - Contradiction detection
  - Conclusion synthesis
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.prompts.finding_extraction import (
    FINDING_EXTRACTION_SYSTEM_PROMPT,
    BATCHED_FINDING_EXTRACTION_SYSTEM_PROMPT,
)
from app.prompts.conclusion_synthesis import CONCLUSION_SYNTHESIS_SYSTEM_PROMPT
from app.prompts.contradiction_detection import CONTRADICTION_DETECTION_SYSTEM_PROMPT
from app.prompts.question_decomposition import DECOMPOSITION_SYSTEM_PROMPT
from app.providers.base import (
    AIProvider,
    ConclusionCandidate,
    ContradictionCandidate,
    FindingCandidate,
    SourceDocumentInput,
    SubQuestionCandidate,
)

logger = logging.getLogger(__name__)


# ─── Structured Response Schemas ─────────────────────────────────────────────

class SubQuestionListResponse(BaseModel):
    sub_questions: List[SubQuestionCandidate]


class FindingListResponse(BaseModel):
    findings: List[FindingCandidate]


class ContradictionListResponse(BaseModel):
    contradictions: List[ContradictionCandidate]


class ConclusionListResponse(BaseModel):
    conclusions: List[ConclusionCandidate]


# ─── Gemini AI Provider ─────────────────────────────────────────────────────

class GeminiAIProvider(AIProvider):
    """
    Production Gemini AI Provider using structured JSON output.
    All synchronous SDK calls are dispatched via asyncio.to_thread.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Gemini AI Provider with model '{self.model_name}'")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai Client: {e}")
        else:
            logger.warning("GEMINI_API_KEY not set. GeminiAIProvider operating in fallback mode.")

    async def decompose_question(self, question: str) -> List[SubQuestionCandidate]:
        """Decompose question into structured sub-inquiries using Gemini."""
        if not self.client:
            return self._fallback_decompose(question)

        prompt = DECOMPOSITION_SYSTEM_PROMPT.format(question=question)

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SubQuestionListResponse,
                temperature=0.2,
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            data = json.loads(response.text)
            parsed = SubQuestionListResponse.model_validate(data)
            return parsed.sub_questions
        except Exception as e:
            logger.error(f"Gemini decompose_question failed: {e}. Using fallback.")
            return self._fallback_decompose(question)

    async def extract_findings_and_evidence(
        self, source_url: str, source_content: str, research_question: str
    ) -> List[FindingCandidate]:
        """Extract findings from a single source (used as batch fallback)."""
        if not self.client:
            return self._fallback_extract_findings(source_url, source_content, research_question)

        truncated_content = source_content[:8000]
        prompt = FINDING_EXTRACTION_SYSTEM_PROMPT.format(
            research_question=research_question,
            source_url=source_url,
            source_content=truncated_content,
            max_findings=settings.MAX_FINDINGS_PER_SOURCE,
        )

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FindingListResponse,
                temperature=0.15,
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            data = json.loads(response.text)
            parsed = FindingListResponse.model_validate(data)
            # Enforce per-source cap
            findings = parsed.findings[:settings.MAX_FINDINGS_PER_SOURCE]
            for f in findings:
                f.source_url = source_url
            return findings
        except Exception as e:
            logger.error(f"Gemini extract_findings failed: {e}. Using fallback.")
            return self._fallback_extract_findings(source_url, source_content, research_question)

    async def extract_findings_from_source_batch(
        self, sources: List[SourceDocumentInput], research_question: str
    ) -> List[FindingCandidate]:
        """
        Extract findings from a batch of source documents in a single Gemini call.
        Enforces per-source finding cap in the prompt.
        """
        if not self.client:
            all_findings = []
            for s in sources:
                f_list = self._fallback_extract_findings(s.url, s.content, research_question)
                for f in f_list:
                    f.source_id = s.source_id
                    f.source_url = s.url
                all_findings.extend(f_list)
            return all_findings

        if not sources:
            return []

        source_url_map = {s.source_id: s.url for s in sources}
        source_id_by_url = {s.url: s.source_id for s in sources}

        sources_text_blocks = []
        for idx, s in enumerate(sources, start=1):
            truncated = s.content[:6000]
            block = (
                f"--- SOURCE DOCUMENT {idx} ---\n"
                f"SOURCE_ID: {s.source_id}\n"
                f"TITLE: {s.title}\n"
                f"URL: {s.url}\n"
                f"TYPE: {s.source_type} (credibility: {s.credibility:.2f})\n"
                f"CONTENT:\n{truncated}\n"
            )
            sources_text_blocks.append(block)

        sources_text = "\n\n".join(sources_text_blocks)
        prompt = BATCHED_FINDING_EXTRACTION_SYSTEM_PROMPT.format(
            research_question=research_question,
            sources_text=sources_text,
            max_findings_per_source=settings.MAX_FINDINGS_PER_SOURCE,
        )

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FindingListResponse,
                temperature=0.15,
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            data = json.loads(response.text)
            parsed = FindingListResponse.model_validate(data)

            # Post-process: ensure source attribution integrity
            validated = []
            for f in parsed.findings:
                if f.source_id and f.source_id in source_url_map:
                    f.source_url = source_url_map[f.source_id]
                elif f.source_url and f.source_url in source_id_by_url:
                    f.source_id = source_id_by_url[f.source_url]
                elif len(sources) == 1:
                    f.source_id = sources[0].source_id
                    f.source_url = sources[0].url
                validated.append(f)

            return validated
        except Exception as e:
            logger.error(f"Gemini batch extraction failed: {e}. Falling back to single-source.")
            all_findings = []
            for s in sources:
                f_list = await self.extract_findings_and_evidence(s.url, s.content, research_question)
                for f in f_list:
                    f.source_id = s.source_id
                    f.source_url = s.url
                all_findings.extend(f_list)
            return all_findings

    async def detect_contradictions_from_findings(
        self, findings: List[Dict[str, Any]]
    ) -> List[ContradictionCandidate]:
        """Identify contradictions between findings using Gemini."""
        if not self.client or len(findings) < 2:
            return []

        findings_text = "\n".join(
            f"Finding {idx+1}: {f.get('statement', '')}"
            for idx, f in enumerate(findings)
        )
        prompt = CONTRADICTION_DETECTION_SYSTEM_PROMPT.format(findings_text=findings_text)

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ContradictionListResponse,
                temperature=0.1,
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            data = json.loads(response.text)
            parsed = ContradictionListResponse.model_validate(data)
            return parsed.contradictions
        except Exception as e:
            logger.error(f"Gemini detect_contradictions failed: {e}")
            return []

    async def generate_conclusions_from_findings(
        self, question: str, findings: List[Dict[str, Any]]
    ) -> List[ConclusionCandidate]:
        """Synthesize conclusions grounded in member findings using Gemini."""
        if not self.client or not findings:
            return self._fallback_generate_conclusions(question, findings)

        findings_text = "\n".join(
            f"- [{f.get('finding_type', 'fact')}] {f.get('statement', '')} (confidence: {f.get('confidence', 0.0):.2f})"
            for f in findings
        )
        prompt = CONCLUSION_SYNTHESIS_SYSTEM_PROMPT.format(
            question=question,
            findings_text=findings_text,
        )

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ConclusionListResponse,
                temperature=0.2,
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            data = json.loads(response.text)
            parsed = ConclusionListResponse.model_validate(data)
            return parsed.conclusions
        except Exception as e:
            logger.error(f"Gemini generate_conclusions failed: {e}. Using fallback.")
            return self._fallback_generate_conclusions(question, findings)

    # ─── Fallback Methods ────────────────────────────────────────────────

    def _fallback_decompose(self, question: str) -> List[SubQuestionCandidate]:
        return [
            SubQuestionCandidate(
                question=f"What are the current adoption trends and operational benchmarks regarding '{question}'?",
                sequence_number=1, priority="high",
                rationale="Market adoption baseline",
            ),
            SubQuestionCandidate(
                question=f"What are the key technical implementations and business ROI associated with '{question}'?",
                sequence_number=2, priority="high",
                rationale="Technical execution & financial impact",
            ),
            SubQuestionCandidate(
                question=f"What risks, compliance constraints, or implementation barriers exist for '{question}'?",
                sequence_number=3, priority="medium",
                rationale="Risk & governance assessment",
            ),
        ]

    def _fallback_extract_findings(
        self, source_url: str, source_content: str, research_question: str
    ) -> List[FindingCandidate]:
        lines = [l.strip() for l in source_content.splitlines() if l.strip() and len(l.strip()) > 30]
        if not lines:
            return []
        first_sentence = lines[0][:200]
        return [
            FindingCandidate(
                statement=first_sentence,
                finding_type="fact",
                confidence=0.60,
                importance="medium",
                source_url=source_url,
                excerpt=first_sentence,
                relevance_score=0.60,
                evidence_type="supporting",
                rationale="Extracted from source content (fallback mode).",
            )
        ]

    def _fallback_generate_conclusions(
        self, question: str, findings: List[Dict[str, Any]]
    ) -> List[ConclusionCandidate]:
        finding_stmts = [f.get("statement", "") for f in findings if f.get("statement")]
        if not finding_stmts:
            return [
                ConclusionCandidate(
                    statement=f"The available evidence is insufficient to fully determine specific claims regarding '{question}'. Further targeted research is recommended.",
                    confidence=0.30,
                    supporting_finding_statements=[],
                    limitations="No validated findings were available for synthesis.",
                )
            ]
        return [
            ConclusionCandidate(
                statement=f"Based on {len(finding_stmts)} validated findings, preliminary evidence exists regarding '{question}', though coverage may be limited.",
                confidence=0.65,
                supporting_finding_statements=finding_stmts[:5],
                limitations="Synthesized from available web evidence; some aspects may lack direct evidence.",
            )
        ]
