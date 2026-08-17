"""
Production Research Pipeline Service.

Clean 9-Stage Architecture:
  1. Question Decomposition & Constraint Preservation (1 LLM call)
  2. Parallel Search Query Execution (no LLM, concurrent)
  3. Deterministic Candidate Scoring & Rank-and-Select Top-N (no LLM)
  4. Bounded Concurrent Content Fetching (no LLM, strict failure contract)
  5. Batched Finding Extraction with Strict Verbatim Evidence Grounding (batched LLM)
  6. Generic Finding Deduplication & Multi-Factor Confidence Calibration (no LLM)
  7. Contradiction Detection on Canonical Findings (1 LLM call)
  8. Conclusion Synthesis with Finding Traceability (1 LLM call)
  9. Telemetry & State Persistence (no LLM)
"""

import asyncio
import re
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.utils import normalize_url, is_near_duplicate
from app.evaluation.confidence import calculate_calibrated_finding_confidence
from app.evaluation.constraint_guard import validate_and_augment_sub_questions
from app.evaluation.deduplication import deduplicate_findings
from app.evaluation.metrics import calculate_research_quality_metrics
from app.evaluation.numeric_guard import validate_numeric_preservation
from app.evaluation.relevance import (
    classify_domain,
    is_hard_excluded,
    score_source,
    apply_domain_diversity,
    SourceScore,
)
from app.models import (
    Conclusion,
    Contradiction,
    Evidence,
    Finding,
    ResearchRun,
    ResearchSource,
    ResearchSubQuestion,
    SourceContent,
)
from app.prompts import PROMPT_VERSIONS
from app.providers.base import SourceDocumentInput
from app.providers.factory import get_ai_provider, get_research_provider
from app.providers.research.web import generate_focused_queries


# ─── Template Finding Detection ──────────────────────────────────────────────

_TEMPLATE_PATTERNS = [
    r"^enterprise research insight regarding",
    r"^empirical evidence from http",
    r"^evidence from .+ indicates",
    r"^source document reference",
    r"^analysis report examining",
    r"^enterprise analysis report",
    r"^enterprise adoption analysis",
    r"^global industry report",
    r"^academic research paper",
    r"^research indicates that generative ai",
    r"^according to sources, there are multiple",
    r"^findings reveal important benefits and risks",
]
_TEMPLATE_RE = re.compile("|".join(_TEMPLATE_PATTERNS), re.IGNORECASE)


def is_template_finding(statement: str) -> bool:
    """Detect generic/template findings that are not meaningful factual claims."""
    if not statement:
        return True
    return bool(_TEMPLATE_RE.search(statement.strip()))


# ─── Pipeline Service ─────────────────────────────────────────────────────────

class ResearchPipelineService:
    def __init__(self, session: AsyncSession, ai_provider=None, research_provider=None):
        self.session = session
        from app.repositories import QuestionRepository, RunRepository, SubQuestionRepository
        self.run_repo = RunRepository(session)
        self.question_repo = QuestionRepository(session)
        self.sub_q_repo = SubQuestionRepository(session)
        self.ai_provider = ai_provider or get_ai_provider()
        self.research_provider = research_provider or get_research_provider()

    async def execute_run(self, run_id: UUID) -> ResearchRun:
        pipeline_start = time.time()
        timing: Dict[str, float] = {}
        warnings_list: List[str] = []

        # Determine execution mode
        ai_p_name = self.ai_provider.__class__.__name__
        res_p_name = self.research_provider.__class__.__name__

        if settings.AI_PROVIDER == "gemini" and getattr(self.ai_provider, "api_key", None):
            execution_mode = "real"
        elif settings.AI_PROVIDER == "gemini":
            execution_mode = "fallback"
        else:
            execution_mode = "mock"

        # ─── 1. Fetch & validate run ─────────────────────────────────────
        run = await self.run_repo.get_by_id(run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ResearchRun '{run_id}' not found.")
        if run.status == "running":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"ResearchRun '{run_id}' is already executing.")
        if run.status == "completed":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ResearchRun '{run_id}' has already completed.")

        question_obj = await self.question_repo.get_by_id(run.question_id)
        if not question_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Associated question '{run.question_id}' not found.")

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        run.error_message = None
        await self.session.flush()

        logger.info(f"[pipeline_start] run_id={run_id} mode={execution_mode} question='{question_obj.question[:80]}'")

        try:
            # ─── STAGE 1: Question Decomposition & Constraint Preservation ───────
            t0 = time.time()
            raw_sub_qs = await self.ai_provider.decompose_question(question_obj.question)
            bounded_sub_qs, constraint_meta = validate_and_augment_sub_questions(
                original_question=question_obj.question,
                sub_questions=raw_sub_qs,
                max_sub_questions=settings.MAX_SUBQUESTIONS,
            )

            persisted_sub_qs: List[ResearchSubQuestion] = []
            for candidate in bounded_sub_qs:
                sub_q = ResearchSubQuestion(
                    research_run_id=run.id,
                    question=candidate.question,
                    sequence_number=candidate.sequence_number,
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
                self.session.add(sub_q)
                persisted_sub_qs.append(sub_q)
            await self.session.flush()
            timing["decomposition_seconds"] = round(time.time() - t0, 2)

            logger.info(f"[stage1_complete] run_id={run_id} sub_questions={len(persisted_sub_qs)}")

            # ─── STAGE 2: Parallel Search Execution ──────────────────────────────
            t0 = time.time()
            search_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SEARCHES)
            search_success_count = 0
            search_failure_count = 0

            # Build query plan across sub-questions
            query_plan: List[Tuple[str, ResearchSubQuestion]] = []
            for sub_q in persisted_sub_qs:
                queries = generate_focused_queries(
                    sub_q.question,
                    max_queries=settings.MAX_SEARCH_QUERIES_PER_SUBQUESTION,
                )
                for q_str in queries:
                    query_plan.append((q_str, sub_q))

            # Execute searches concurrently with bounded semaphore
            async def _execute_single_search(query_str: str, sub_q: ResearchSubQuestion, delay_offset: float = 0.0):
                if delay_offset > 0:
                    await asyncio.sleep(delay_offset)
                async with search_semaphore:
                    try:
                        results = await self.research_provider.search(
                            query_str, max_results=settings.RESEARCH_RESULTS_PER_QUERY
                        )
                        return query_str, sub_q, results, None
                    except Exception as s_err:
                        return query_str, sub_q, [], s_err

            search_tasks = [
                _execute_single_search(q, sq, delay_offset=idx * 0.15)
                for idx, (q, sq) in enumerate(query_plan)
            ]
            search_responses = await asyncio.gather(*search_tasks)

            # ─── STAGE 3: Deterministic Candidate Scoring & Rank-and-Select Top-N ──
            seen_canonical_urls: Set[str] = set()
            seen_titles_by_domain: Dict[str, List[str]] = {}
            source_type_counter: Counter = Counter()
            discovered_count = 0
            rejected_sources_list: List[dict] = []
            valid_candidates: List[dict] = []

            for query_str, sub_q, search_results, s_err in search_responses:
                if s_err is not None:
                    search_failure_count += 1
                    warnings_list.append(f"Search query error for '{query_str}': {s_err}")
                    continue

                search_success_count += 1

                for res in search_results:
                    canonical_url = normalize_url(res.url)
                    if not canonical_url or canonical_url in seen_canonical_urls:
                        continue

                    # Near-duplicate title/domain check
                    domain = res.publisher or ""
                    is_dup = False
                    for existing_title in seen_titles_by_domain.get(domain, []):
                        if is_near_duplicate(res.title, domain, existing_title, domain):
                            is_dup = True
                            break
                    if is_dup:
                        continue

                    seen_canonical_urls.add(canonical_url)
                    seen_titles_by_domain.setdefault(domain, []).append(res.title)
                    discovered_count += 1

                    # Score candidate deterministically
                    score_res: SourceScore = score_source(
                        title=res.title,
                        snippet=res.snippet,
                        url=canonical_url,
                        query=query_str,
                        sub_question=sub_q.question,
                    )
                    source_type_counter[score_res.source_type] += 1

                    if score_res.is_hard_excluded:
                        # Hard excluded by policy (social media, forum, dictionary, etc.)
                        rejected_sources_list.append({
                            "url": canonical_url,
                            "title": res.title,
                            "source_type": score_res.source_type,
                            "reason": score_res.exclusion_reason,
                        })
                        source = ResearchSource(
                            research_run_id=run.id,
                            title=res.title,
                            url=canonical_url,
                            publisher=res.publisher,
                            published_at=res.published_at,
                            source_type=score_res.source_type,
                            credibility_score=res.credibility_score,
                            metadata_json={
                                "query": query_str,
                                "provider": "ddgs",
                                "relevance": {"score": 0.0, "reason": score_res.exclusion_reason},
                                "rejection_reason": score_res.exclusion_reason,
                                "lifecycle_state": "REJECTED",
                                "is_evidence_eligible": False,
                            },
                        )
                        self.session.add(source)
                        continue

                    valid_candidates.append({
                        "res": res,
                        "url": canonical_url,
                        "query": query_str,
                        "sub_q": sub_q,
                        "score": score_res,
                    })

            # Sort all valid candidates by composite relevance score descending
            valid_candidates.sort(key=lambda x: x["score"].relevance_score, reverse=True)

            # Apply domain diversity and select Top-N sources
            selected_candidates = apply_domain_diversity(
                valid_candidates,
                max_per_domain=settings.MAX_SOURCES_PER_DOMAIN,
                max_total=settings.MAX_SELECTED_SOURCES,
            )
            selected_urls = {c["url"] for c in selected_candidates}

            # Persist unselected candidates as REJECTED for complete auditability
            for cand in valid_candidates:
                if cand["url"] not in selected_urls:
                    res = cand["res"]
                    rejected_sources_list.append({
                        "url": cand["url"],
                        "title": res.title,
                        "source_type": cand["score"].source_type,
                        "reason": "RANK_BELOW_TOP_N",
                    })
                    source = ResearchSource(
                        research_run_id=run.id,
                        title=res.title,
                        url=cand["url"],
                        publisher=res.publisher,
                        published_at=res.published_at,
                        source_type=cand["score"].source_type,
                        credibility_score=res.credibility_score,
                        metadata_json={
                            "query": cand["query"],
                            "provider": "ddgs",
                            "relevance": {
                                "score": cand["score"].relevance_score,
                                "title_match": cand["score"].title_match,
                                "snippet_match": cand["score"].snippet_match,
                                "concept_match": cand["score"].concept_match,
                                "domain_quality": cand["score"].domain_quality,
                            },
                            "rejection_reason": "RANK_BELOW_TOP_N",
                            "lifecycle_state": "REJECTED",
                            "is_evidence_eligible": False,
                        },
                    )
                    self.session.add(source)

            # Persist selected candidates as ELIGIBLE
            persisted_selected_sources: List[Tuple[ResearchSource, dict]] = []
            for cand in selected_candidates:
                res = cand["res"]
                source = ResearchSource(
                    research_run_id=run.id,
                    title=res.title,
                    url=cand["url"],
                    publisher=res.publisher,
                    published_at=res.published_at,
                    source_type=cand["score"].source_type,
                    credibility_score=res.credibility_score,
                    metadata_json={
                        "query": cand["query"],
                        "provider": "ddgs",
                        "relevance": {
                            "score": cand["score"].relevance_score,
                            "title_match": cand["score"].title_match,
                            "snippet_match": cand["score"].snippet_match,
                            "concept_match": cand["score"].concept_match,
                            "domain_quality": cand["score"].domain_quality,
                        },
                        "lifecycle_state": "ELIGIBLE",
                        "is_evidence_eligible": False,
                    },
                )
                self.session.add(source)
                persisted_selected_sources.append((source, cand))

            await self.session.flush()
            timing["search_and_ranking_seconds"] = round(time.time() - t0, 2)
            logger.info(
                f"[stage2_3_complete] run_id={run_id} discovered={discovered_count} "
                f"valid_candidates={len(valid_candidates)} selected={len(selected_candidates)} "
                f"time={timing['search_and_ranking_seconds']}s"
            )

            # ─── STAGE 4: Bounded Concurrent Content Fetching ────────────────────
            t0 = time.time()
            fetch_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_FETCHES)
            fetch_success_count = 0
            failed_sources_count = 0
            failed_sources_list: List[dict] = []
            successful_sources_list: List[dict] = []

            # Map of source.id -> (ResearchSource, SourceContent)
            eligible_sources: Dict[UUID, Tuple[ResearchSource, SourceContent]] = {}

            async def _fetch_one(source: ResearchSource, cand_info: dict):
                nonlocal fetch_success_count, failed_sources_count
                async with fetch_semaphore:
                    try:
                        doc = await self.research_provider.fetch_content(source.url)
                    except Exception as fetch_err:
                        doc = None
                        warnings_list.append(f"Fetch exception for '{source.url}': {fetch_err}")

                    if doc is None or doc.metadata.get("status") != "success" or not doc.content.strip():
                        failed_sources_count += 1
                        http_code = doc.metadata.get("http_status") if doc else None
                        error_msg = doc.metadata.get("error", "unknown") if doc else "exception"
                        failure_type = doc.metadata.get("failure_type", "unknown") if doc else "exception"
                        fail_reason = f"HTTP_{http_code}" if http_code else f"FETCH_FAILED_{failure_type.upper()}"

                        failed_sources_list.append({
                            "url": source.url,
                            "title": source.title,
                            "http_status": http_code,
                            "failure_type": failure_type,
                            "error": str(error_msg)[:100],
                        })

                        content_obj = SourceContent(
                            source_id=source.id,
                            content="",
                            content_hash=None,
                            word_count=0,
                            extraction_status="failed",
                            metadata_json={
                                "status": "failed",
                                "http_status": http_code,
                                "error": error_msg,
                                "failure_type": failure_type,
                                "lifecycle_state": "FETCH_FAILED",
                                "rejection_reason": fail_reason,
                                "is_evidence_eligible": False,
                            },
                        )
                        self.session.add(content_obj)

                        source_meta = source.metadata_json or {}
                        source_meta["lifecycle_state"] = "FETCH_FAILED"
                        source_meta["fetch_http_status"] = http_code
                        source_meta["rejection_reason"] = fail_reason
                        source_meta["is_evidence_eligible"] = False
                        source.metadata_json = source_meta
                        return

                    fetch_success_count += 1
                    successful_sources_list.append({
                        "url": source.url,
                        "title": source.title,
                        "http_status": doc.metadata.get("http_status", 200),
                        "word_count": doc.word_count,
                    })

                    content_obj = SourceContent(
                        source_id=source.id,
                        content=doc.content,
                        content_hash=doc.content_hash,
                        word_count=doc.word_count,
                        extraction_status="success",
                        metadata_json={
                            "status": "success",
                            "http_status": doc.metadata.get("http_status"),
                            "lifecycle_state": "EVIDENCE_ELIGIBLE",
                            "is_evidence_eligible": True,
                        },
                    )
                    self.session.add(content_obj)

                    source_meta = source.metadata_json or {}
                    source_meta["lifecycle_state"] = "EVIDENCE_ELIGIBLE"
                    source_meta["is_evidence_eligible"] = True
                    source.metadata_json = source_meta

                    eligible_sources[source.id] = (source, content_obj)

            if persisted_selected_sources:
                await asyncio.gather(*[_fetch_one(s, c) for s, c in persisted_selected_sources])
            await self.session.flush()

            timing["fetch_seconds"] = round(time.time() - t0, 2)
            logger.info(
                f"[stage4_complete] run_id={run_id} fetch_success={fetch_success_count} "
                f"failed={failed_sources_count} eligible={len(eligible_sources)} "
                f"time={timing['fetch_seconds']}s"
            )

            # ─── STAGE 5: Batched Finding Extraction with Strict Grounding ───────
            t0 = time.time()
            raw_candidates: List[dict] = []
            unsupported_findings_count = 0

            batch_size = max(1, settings.EXTRACTION_BATCH_SIZE)
            eligible_items = list(eligible_sources.items())  # (source_id, (source, content_obj))
            source_batches = [
                eligible_items[i : i + batch_size] for i in range(0, len(eligible_items), batch_size)
            ]

            batch_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_EXTRACTIONS)

            async def _extract_batch(batch_items):
                async with batch_semaphore:
                    doc_inputs = [
                        SourceDocumentInput(
                            source_id=str(sid),
                            title=s.title,
                            url=s.url,
                            source_type=s.source_type,
                            credibility=s.credibility_score or 0.70,
                            content=c.content,
                        )
                        for sid, (s, c) in batch_items
                    ]
                    try:
                        return await self.ai_provider.extract_findings_from_source_batch(
                            doc_inputs, research_question=question_obj.question
                        )
                    except Exception as ext_err:
                        warnings_list.append(f"Batch extraction error: {ext_err}")
                        return []

            if source_batches:
                batch_tasks = [_extract_batch(b) for b in source_batches]
                batch_results = await asyncio.gather(*batch_tasks)

                for b_items, cand_list in zip(source_batches, batch_results):
                    batch_source_map = {str(sid): (s, c) for sid, (s, c) in b_items}
                    batch_url_map = {s.url: (s, c) for sid, (s, c) in b_items}

                    for cand in cand_list:
                        # 1. Reject template / generic findings
                        if is_template_finding(cand.statement):
                            unsupported_findings_count += 1
                            continue

                        # Resolve target source document
                        target_source = None
                        target_content_obj = None
                        if cand.source_id and cand.source_id in batch_source_map:
                            target_source, target_content_obj = batch_source_map[cand.source_id]
                        elif cand.source_url and cand.source_url in batch_url_map:
                            target_source, target_content_obj = batch_url_map[cand.source_url]
                        elif len(b_items) == 1:
                            target_source, target_content_obj = b_items[0][1]

                        if not target_source or not target_content_obj:
                            unsupported_findings_count += 1
                            continue

                        # 2. Strict Evidence Grounding: Verbatim excerpt check only
                        excerpt_clean = (cand.excerpt or "").strip()
                        if not excerpt_clean:
                            unsupported_findings_count += 1
                            continue

                        excerpt_valid = (
                            excerpt_clean in target_content_obj.content
                            or excerpt_clean[:100] in target_content_obj.content
                        )

                        if not excerpt_valid:
                            # Reject finding — no fuzzy fallback manufactured
                            unsupported_findings_count += 1
                            continue

                        # 3. Numeric Claim Protection Guard
                        is_num_valid, num_violations = validate_numeric_preservation(cand.statement, excerpt_clean)
                        if not is_num_valid:
                            warnings_list.append(f"Numeric range alert for '{cand.statement[:60]}': {num_violations}")

                        source_relevance = (target_source.metadata_json or {}).get("relevance", {}).get("score", 0.70)

                        raw_candidates.append({
                            "statement": cand.statement,
                            "finding_type": cand.finding_type,
                            "importance": cand.importance,
                            "confidence": cand.confidence,
                            "source_id": target_source.id,
                            "source_url": target_source.url,
                            "source_type": target_source.source_type,
                            "credibility": target_source.credibility_score or 0.70,
                            "relevance": source_relevance,
                            "source": target_source,
                            "content_obj": target_content_obj,
                            "excerpt": excerpt_clean,
                            "evidence_relevance": cand.relevance_score,
                            "evidence_type": cand.evidence_type,
                        })

            timing["extraction_seconds"] = round(time.time() - t0, 2)

            # ─── STAGE 6: Finding Deduplication & Calibrated Persistence ─────────
            t0 = time.time()
            findings_before_deduplication = len(raw_candidates)

            canonical_groups, duplicate_findings_merged = deduplicate_findings(
                raw_candidates, similarity_threshold=settings.DEDUP_SIMILARITY_THRESHOLD
            )

            # Apply global findings cap
            if len(canonical_groups) > settings.MAX_FINDINGS_PER_RUN:
                canonical_groups = canonical_groups[:settings.MAX_FINDINGS_PER_RUN]

            persisted_findings: List[Finding] = []
            finding_statement_map: Dict[str, Finding] = {}
            total_evidence_count = 0
            grounded_findings_count = len(canonical_groups)

            for grp in canonical_groups:
                evidence_list = grp.get("evidence", [])
                distinct_sources_count = len({e["source_id"] for e in evidence_list}) if evidence_list else 1

                source_relevances = [e.get("relevance", 0.70) for e in evidence_list]
                source_credibilities = [e.get("credibility", 0.75) for e in evidence_list]
                avg_relevance = sum(source_relevances) / len(source_relevances) if source_relevances else 0.70
                avg_credibility = sum(source_credibilities) / len(source_credibilities) if source_credibilities else 0.75

                calibrated = calculate_calibrated_finding_confidence(
                    evidence_match_score=1.0,
                    source_relevance=avg_relevance,
                    source_credibility=avg_credibility,
                    distinct_sources_count=distinct_sources_count,
                    is_contradicted=False,
                )

                finding = Finding(
                    research_run_id=run.id,
                    statement=grp["statement"],
                    finding_type=grp["finding_type"],
                    confidence=calibrated["confidence"],
                    importance=grp["importance"],
                )
                self.session.add(finding)
                await self.session.flush()
                persisted_findings.append(finding)
                finding_statement_map[finding.statement] = finding

                for merged_stmt in grp.get("merged_statements", []):
                    finding_statement_map[merged_stmt] = finding

                for ev_item in evidence_list:
                    evidence = Evidence(
                        finding_id=finding.id,
                        source_id=ev_item["source_id"],
                        source_content_id=ev_item["content_obj"].id,
                        excerpt=ev_item["excerpt"],
                        relevance_score=min(1.0, max(0.0, ev_item["evidence_relevance"])),
                        evidence_type=ev_item["evidence_type"],
                    )
                    self.session.add(evidence)
                    total_evidence_count += 1

            await self.session.flush()
            timing["deduplication_seconds"] = round(time.time() - t0, 2)
            logger.info(
                f"[stage6_complete] run_id={run_id} raw={findings_before_deduplication} "
                f"canonical={grounded_findings_count} merged={duplicate_findings_merged} "
                f"evidence={total_evidence_count} time={timing['deduplication_seconds']}s"
            )

            # ─── STAGE 7: Contradiction Detection on Canonical Findings ──────────
            t0 = time.time()
            canonical_findings_dicts = [
                {
                    "statement": f.statement,
                    "finding_type": f.finding_type,
                    "confidence": f.confidence,
                    "importance": f.importance,
                }
                for f in persisted_findings
            ]

            contradiction_candidates = await self.ai_provider.detect_contradictions_from_findings(canonical_findings_dicts)
            persisted_contradictions: List[Contradiction] = []
            contradiction_cat_counter: Counter = Counter()

            for c_cand in contradiction_candidates:
                f_a = finding_statement_map.get(c_cand.finding_a_statement)
                f_b = finding_statement_map.get(c_cand.finding_b_statement)

                if f_a and f_b and f_a.id != f_b.id:
                    cat = c_cand.contradiction_category or "DIRECT_CONTRADICTION"
                    contradiction_cat_counter[cat] += 1
                    contradiction = Contradiction(
                        research_run_id=run.id,
                        finding_a_id=f_a.id,
                        finding_b_id=f_b.id,
                        description=c_cand.description,
                        severity=c_cand.severity,
                        contradiction_category=cat,
                        resolution_status="unresolved",
                    )
                    self.session.add(contradiction)
                    persisted_contradictions.append(contradiction)

            await self.session.flush()
            timing["contradiction_seconds"] = round(time.time() - t0, 2)

            # ─── STAGE 8: Conclusion Generation on Canonical Findings ────────────
            t0 = time.time()
            conclusion_candidates = await self.ai_provider.generate_conclusions_from_findings(
                question_obj.question, canonical_findings_dicts
            )
            persisted_conclusions: List[Conclusion] = []
            conclusions_with_findings = 0

            for conc_cand in conclusion_candidates:
                conclusion = Conclusion(
                    research_run_id=run.id,
                    statement=conc_cand.statement,
                    confidence=min(1.0, max(0.0, conc_cand.confidence)),
                )

                for stmt_ref in conc_cand.supporting_finding_statements:
                    member_finding = finding_statement_map.get(stmt_ref)
                    if member_finding and member_finding not in conclusion.findings:
                        conclusion.findings.append(member_finding)

                if not conclusion.findings and persisted_findings:
                    for f in persisted_findings[:5]:
                        conclusion.findings.append(f)

                if conclusion.findings:
                    conclusions_with_findings += 1

                self.session.add(conclusion)
                persisted_conclusions.append(conclusion)

            await self.session.flush()
            timing["synthesis_seconds"] = round(time.time() - t0, 2)

            # ─── STAGE 9: Telemetry, Metrics & Run Finalization ──────────────────
            total_duration = round(time.time() - pipeline_start, 2)
            timing["total_seconds"] = total_duration

            quality_metrics = calculate_research_quality_metrics(
                discovered_sources_count=discovered_count,
                relevant_sources_count=len(selected_candidates),
                rejected_irrelevant_count=len(rejected_sources_list),
                fetch_success_count=fetch_success_count,
                failed_sources_count=failed_sources_count,
                evidence_eligible_count=len(eligible_sources),
                findings_count=grounded_findings_count + unsupported_findings_count,
                grounded_findings_count=grounded_findings_count,
                unsupported_findings_count=unsupported_findings_count,
                contradictions_count=len(persisted_contradictions),
                conclusions_count=len(persisted_conclusions),
                conclusions_with_findings_count=conclusions_with_findings,
                execution_mode=execution_mode,
                source_type_distribution=dict(source_type_counter),
                timing_breakdown=timing,
            )

            existing_meta = run.metadata_json or {}
            execution_metadata = {
                **existing_meta,
                "execution_mode": execution_mode,
                "ai_provider": ai_p_name,
                "ai_model": settings.GEMINI_MODEL if settings.AI_PROVIDER == "gemini" else "mock-model",
                "research_provider": res_p_name,
                "prompt_versions": PROMPT_VERSIONS,
                "subquestions_count": len(persisted_sub_qs),
                # Search telemetry
                "search_query_count": len(query_plan),
                "search_success_count": search_success_count,
                "search_failure_count": search_failure_count,
                "search_parallelism": settings.MAX_CONCURRENT_SEARCHES,
                "search_duration_seconds": timing.get("search_and_ranking_seconds", 0.0),
                # Extraction telemetry
                "extraction_batch_count": len(source_batches),
                "extraction_source_count": len(eligible_items),
                "extraction_parallelism": settings.MAX_CONCURRENT_EXTRACTIONS,
                "extraction_duration_seconds": timing.get("extraction_seconds", 0.0),
                # Deduplication telemetry
                "findings_before_deduplication": findings_before_deduplication,
                "findings_after_deduplication": grounded_findings_count,
                "duplicate_findings_merged": duplicate_findings_merged,
                # Source lifecycle & auditability
                "discovered_sources": discovered_count,
                "selected_sources": len(selected_candidates),
                "relevant_sources": len(selected_candidates),
                "rejected_sources": rejected_sources_list,
                "rejected_sources_count": len(rejected_sources_list),
                "rejected_irrelevant_sources": rejected_sources_list,
                "rejected_irrelevant_count": len(rejected_sources_list),
                "successful_sources": successful_sources_list,
                "successful_sources_count": fetch_success_count,
                "failed_sources": failed_sources_list,
                "failed_sources_count": failed_sources_count,
                "evidence_eligible_count": len(eligible_sources),
                "source_diversity": {
                    "unique_domains_count": len(seen_titles_by_domain),
                    "max_sources_per_domain": settings.MAX_SOURCES_PER_DOMAIN,
                    "source_types": dict(source_type_counter),
                },
                # Findings & evidence metrics
                "finding_count": grounded_findings_count,
                "findings_count": grounded_findings_count,
                "grounded_findings_count": grounded_findings_count,
                "unsupported_findings_count": unsupported_findings_count,
                "evidence_count": total_evidence_count,
                "contradiction_count": len(persisted_contradictions),
                "contradictions_count": len(persisted_contradictions),
                "contradictions_by_category": dict(contradiction_cat_counter),
                "conclusions_count": len(persisted_conclusions),
                "duration_seconds": total_duration,
                "total_runtime": total_duration,
                "constraint_preservation": constraint_meta,
                "warnings": warnings_list,
                "quality_metrics": quality_metrics,
            }

            run.metadata_json = execution_metadata
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            await self.session.commit()

            logger.info(
                f"[pipeline_complete] run_id={run_id} mode={execution_mode} "
                f"duration={total_duration}s discovered={discovered_count} "
                f"selected={len(selected_candidates)} eligible={len(eligible_sources)} "
                f"canonical_findings={grounded_findings_count} merged={duplicate_findings_merged} "
                f"evidence={total_evidence_count}"
            )
            return run

        except Exception as e:
            await self.session.rollback()
            err_run = await self.run_repo.get_by_id(run_id)
            if err_run:
                err_run.status = "failed"
                err_run.error_message = str(e)
                err_run.completed_at = datetime.now(timezone.utc)
                await self.session.commit()

            logger.error(f"[pipeline_failed] run_id={run_id} error='{str(e)}'", exc_info=True)
            raise
