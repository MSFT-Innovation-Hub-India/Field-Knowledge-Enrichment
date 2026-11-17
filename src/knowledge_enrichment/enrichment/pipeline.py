"""The enrichment pipeline: classify issue type -> assess/merge (existing) or draft new SOP -> guardrails -> index."""
from __future__ import annotations

import logging
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone

from ..corpus import Incident, parse_sop_text, sop_to_catalog_entry
from ..kb import KnowledgeIndex, LlmClient
from ..kb import chunking
from ..kb.chunking import SOURCE_FIELD
from ..settings import Settings
from . import guardrails as gr
from . import prompts as pr
from .audit import AuditLog
from .catalog import Catalog, body_of
from .models import (
    AssessResult, AuditRecord, ClassifyResult, MergeResult, NewSopDraft, Outcome, SafetyJudgement, Ticket,
)

log = logging.getLogger(__name__)
FAMILY = {"battery": "BAT", "station": "STN"}
NOT_ESTABLISHED = "Not yet established"
ERROR_CODE = re.compile(r"\b[EW]-\d{3}\b")


class EnrichmentEngine:
    def __init__(self, settings: Settings, llm: LlmClient, kb: KnowledgeIndex, catalog: Catalog, audit: AuditLog):
        self.s = settings
        self.llm = llm
        self.kb = kb
        self.catalog = catalog
        self.audit = audit
        self._sop_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._new_sop_lock = threading.Lock()

    # ------------------------------------------------------------------------------------------
    def process(self, job_id: str, ticket: Ticket) -> AuditRecord:
        t0 = time.monotonic()
        rec = AuditRecord(job_id=job_id, ticket_id=ticket.ticket_id, asset_id=ticket.asset_id,
                          asset_type=ticket.asset_type, ts=chunking.now_iso())
        try:
            self._run(ticket, rec)
        except Exception as exc:
            log.exception("Enrichment failed for %s", ticket.ticket_id)
            rec.outcome = Outcome.ERROR.value
            rec.error = f"{type(exc).__name__}: {exc}"[:500]
        rec.duration_ms = int((time.monotonic() - t0) * 1000)
        self.audit.write(rec)
        return rec

    # ------------------------------------------------------------------------------------------
    def _run(self, ticket: Ticket, rec: AuditRecord) -> None:
        if gr.trivial_fix(ticket.fix_applied):
            rec.outcome, rec.rationale = Outcome.SKIPPED.value, "Fix text too short or not actionable"
            return

        safety = gr.check_input_safety(ticket.issue, ticket.fix_applied, ticket.root_cause, ticket.parts_replaced)
        if not safety.passed:
            rec.outcome, rec.guardrails, rec.rationale = Outcome.REJECTED.value, safety.as_dict(), "Input failed safety scan"
            return

        entries = self.catalog.entries(ticket.asset_type)
        catalog_version = self.catalog.version
        cls = self._classify(ticket, entries)
        rec.classification = cls.model_dump()
        rec.rationale = cls.rationale
        if cls.injection_suspected:
            rec.outcome = Outcome.REJECTED.value
            rec.guardrails = {"passed": False, "failed": ["model flagged prompt injection"]}
            return

        valid_ids = {e.sop_id for e in entries}
        if cls.matched_sop_id and cls.matched_sop_id in valid_ids and cls.confidence >= self.s.match_min_confidence:
            self._existing(ticket, cls.matched_sop_id, rec)
        elif cls.matched_sop_id is None and cls.confidence >= self.s.new_issue_min_confidence and cls.fix_is_substantive:
            self._new_issue(ticket, cls, entries, catalog_version, rec)
        else:
            rec.outcome = Outcome.AMBIGUOUS.value

    def _classify(self, ticket: Ticket, entries) -> ClassifyResult:
        return self.llm.complete_json(
            pr.CLASSIFY_SYSTEM,
            pr.classify_user(ticket.asset_type, ticket.issue, ticket.fix_applied, ticket.root_cause, [e.as_prompt_dict() for e in entries]),
            ClassifyResult,
        )

    # ---- existing issue type -----------------------------------------------------------------
    def _existing(self, ticket: Ticket, sop_id: str, rec: AuditRecord) -> None:
        if not self.s.enrich_existing_sops:
            rec.outcome = Outcome.EXISTING_UNTOUCHED.value
            return

        with self._sop_locks[sop_id]:
            base = self.catalog.sop_text(sop_id)
            field_doc = self.kb.get_document(f"{sop_id}__field")
            field_text = body_of(field_doc["content"]) if field_doc else ""

            # Cheap shortcut: fix is near-identical to what is already indexed for this SOP.
            query = f"{ticket.issue}\n{ticket.fix_applied}"
            for doc, cosine in self.kb.semantic_neighbors(query, top=5):
                if doc.get("sop_id") == sop_id and doc.get("doc_type") in ("sop_section", "field_experience") \
                        and cosine >= self.s.enrich_duplicate_cosine:
                    rec.verdict, rec.outcome = "duplicate", Outcome.DUPLICATE.value
                    rec.rationale = f"Near-identical to indexed content {doc.get('id')} (cosine {cosine:.2f})"
                    return

            assess = self.llm.complete_json(
                pr.ASSESS_SYSTEM,
                pr.assess_user(ticket.asset_type, ticket.issue, ticket.fix_applied, ticket.root_cause, base, field_text),
                AssessResult,
            )
            rec.verdict, rec.rationale = assess.verdict, assess.rationale
            if assess.injection_suspected:
                rec.outcome, rec.guardrails = Outcome.REJECTED.value, {"passed": False, "failed": ["model flagged prompt injection"]}
                return
            if assess.verdict == "duplicate":
                rec.outcome = Outcome.DUPLICATE.value
                return
            if assess.verdict == "no_value" or assess.confidence < self.s.assess_min_confidence or not assess.new_facts:
                rec.outcome = Outcome.NO_VALUE.value
                return

            ticket_ref = f"{ticket.ticket_id} on {ticket.asset_id} ({ticket.logged_date or 'date n/a'})"
            merge = self.llm.complete_json(pr.MERGE_SYSTEM, pr.merge_user(field_text, assess.new_facts, ticket_ref), MergeResult)
            markdown = merge.merged_markdown.strip()

            allowed = [ticket.input_text(), base, field_text, "\n".join(assess.new_facts), ticket_ref]
            result = gr.check_field_structure(markdown)
            g2 = gr.check_generated(markdown, allowed, gr.MAX_FIELD_CHARS, field_text, gr.MAX_FIELD_GROWTH)
            for reason in g2.failed:
                result.fail(reason)
            if result.passed:
                judge = self.llm.complete_json(pr.SAFETY_JUDGE_SYSTEM, pr.safety_user(base, markdown), SafetyJudgement)
                if judge.contradicts_safety:
                    result.fail(f"contradicts SOP safety: {judge.reason}")
            rec.guardrails = result.as_dict()
            rec.before, rec.after = field_text, markdown
            if not result.passed:
                rec.outcome = Outcome.REJECTED.value
                return

            issue_type, applies_to, error_codes, severity = self.catalog.sop_meta(sop_id, ticket.asset_type)
            revision = int(field_doc.get("revision") or 0) + 1 if field_doc else 1
            tickets = list(dict.fromkeys([*(field_doc.get("source_tickets") or []), ticket.ticket_id])) if field_doc else [ticket.ticket_id]
            chunks = [
                chunking.field_experience_chunk(sop_id, issue_type, applies_to, error_codes, severity, markdown, revision, tickets, field_text or None),
                self._incident_chunk(ticket, sop_id, issue_type),
            ]
            if self.s.enrich_require_approval:
                rec.outcome = Outcome.NEEDS_APPROVAL.value
                return
            rec.chunk_ids = self.kb.upsert_chunks(chunks)
            rec.outcome = Outcome.AUGMENTED.value

    # ---- new issue type ----------------------------------------------------------------------
    def _new_issue(self, ticket: Ticket, cls: ClassifyResult, entries, catalog_version: int, rec: AuditRecord) -> None:
        family = FAMILY[ticket.asset_type]
        with self._new_sop_lock:
            if self.catalog.version != catalog_version:
                # Another ticket created a SOP while we were classifying: re-check against the fresh catalog
                # so the same new issue type never gets two SOPs.
                entries = self.catalog.entries(ticket.asset_type)
                cls = self._classify(ticket, entries)
                rec.classification = {**cls.model_dump(), "rechecked": True}
                rec.rationale = cls.rationale
                if cls.matched_sop_id and cls.matched_sop_id in {e.sop_id for e in entries} and cls.confidence >= self.s.match_min_confidence:
                    self._existing(ticket, cls.matched_sop_id, rec)
                    return
                if cls.matched_sop_id is not None or cls.confidence < self.s.new_issue_min_confidence or not cls.fix_is_substantive:
                    rec.outcome = Outcome.AMBIGUOUS.value
                    return
            titles = [e.issue_type for e in entries]
            draft = self.llm.complete_json(
                pr.DRAFT_SYSTEM,
                pr.draft_user(ticket.asset_type, ticket.issue, ticket.fix_applied, ticket.root_cause, ticket.parts_replaced, titles),
                NewSopDraft,
            )
            title = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", draft.issue_type_title or cls.proposed_issue_type or "")).strip()
            if not title:
                rec.outcome, rec.rationale = Outcome.AMBIGUOUS.value, "No usable issue-type title"
                return
            if title.lower() in {t.lower() for t in titles}:
                rec.outcome, rec.rationale = Outcome.AMBIGUOUS.value, f"Drafted title '{title}' duplicates an existing issue type"
                return

            input_text = ticket.input_text()
            severity = draft.severity.strip() if re.fullmatch(r"P[123]", draft.severity.strip()) and draft.severity.strip() in input_text else NOT_ESTABLISHED
            error_codes = sorted({c for c in draft.error_codes if ERROR_CODE.fullmatch(c) and c in input_text})

            generated = "\n\n".join([draft.symptoms, draft.safety, draft.troubleshooting_steps,
                                     draft.resolution_verification, draft.root_causes, draft.summary])
            result = gr.check_generated(generated, [input_text], gr.MAX_NEW_SOP_CHARS)

            sop_id = f"SOP-{family}-F{self.catalog.next_field_number(family):03d}"
            markdown = self._assemble_sop(sop_id, ticket, title, severity, error_codes, draft)
            for reason in gr.check_new_sop_structure(markdown).failed:
                result.fail(reason)
            rec.guardrails = result.as_dict()
            rec.after = markdown
            if not result.passed:
                rec.outcome = Outcome.REJECTED.value
                return

            file_name = f"{sop_id}_{title.replace(' ', '_')}.md"
            sop = parse_sop_text(file_name, markdown, self.catalog.mapping, origin="field")
            sop.applies_to = [ticket.asset_type]
            chunks = chunking.sop_section_chunks(sop, SOURCE_FIELD, 1, [ticket.ticket_id])
            chunks.append(chunking.sop_catalog_chunk(sop, draft.summary.strip()[:400], SOURCE_FIELD, 1, [ticket.ticket_id]))
            chunks.append(self._incident_chunk(ticket, sop_id, title))
            rec.classification["new_sop_id"] = sop_id
            if self.s.enrich_require_approval:
                rec.outcome = Outcome.NEEDS_APPROVAL.value
                return
            rec.chunk_ids = self.kb.upsert_chunks(chunks)
            self.catalog.register_field_sop(sop_to_catalog_entry(sop))
            rec.outcome = Outcome.NEW_SOP_CREATED.value

    # ---- helpers -----------------------------------------------------------------------------
    def _incident_chunk(self, ticket: Ticket, sop_id: str, issue_type: str) -> dict:
        codes = ERROR_CODE.findall(ticket.input_text())
        inc = Incident(
            asset_id=ticket.asset_id, asset_type=ticket.asset_type, ticket_id=ticket.ticket_id,
            date=ticket.logged_date, issue_code=codes[0] if codes else "", symptoms=ticket.issue,
            root_cause=ticket.root_cause or NOT_ESTABLISHED, resolution=ticket.fix_applied,
            status="Resolved", linked_sop=sop_id,
        )
        return chunking.incident_chunk(inc, source=SOURCE_FIELD, sop_title=issue_type)

    def _assemble_sop(self, sop_id: str, ticket: Ticket, title: str, severity: str, error_codes: list[str], d: NewSopDraft) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        label = ticket.asset_type.capitalize()
        issue_line = re.sub(r"\s+", " ", ticket.issue)[:200]
        return f"""# {sop_id}: {title}

| Field | Value |
|---|---|
| SOP ID | {sop_id} |
| Applies to | {label} |
| Error codes | {', '.join(error_codes) if error_codes else 'None recorded'} |
| Severity | {severity} |
| Owner | Not yet assigned |
| Version | 0.1 ({today}) |
| Status | Field-derived - not yet reviewed |
| Source tickets | {ticket.ticket_id} |

## 1. Symptoms
{d.symptoms.strip()}

## 2. Safety
{d.safety.strip()}

## 3. Troubleshooting steps
{d.troubleshooting_steps.strip()}

## 4. Resolution verification
{d.resolution_verification.strip()}

## 5. Root causes seen
{d.root_causes.strip()}

## 6. Reference past incidents
- {ticket.ticket_id} ({ticket.asset_id}, {ticket.logged_date or today}): {issue_line}
"""
