"""Data models for tickets, model outputs, outcomes and audit."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

AssetType = Literal["battery", "station"]
Criticality = Literal["urgent", "priority", "normal"]


class Ticket(BaseModel):
    ticket_id: str = Field(min_length=1, max_length=64)
    asset_id: str = Field(min_length=1, max_length=64)
    asset_type: AssetType
    issue: str = Field(min_length=1, max_length=2000)
    logged_date: str = Field(default="", max_length=32)
    criticality: Criticality | None = None
    fix_applied: str = Field(default="", max_length=4000)
    root_cause: str = Field(default="", max_length=1000)
    parts_replaced: str = Field(default="", max_length=500)
    time_to_resolve_hours: float | None = None
    technician: str = Field(default="", max_length=100)

    def input_text(self) -> str:
        """Everything the technician/operator typed (the allowed source of facts)."""
        return "\n".join(
            x for x in [self.issue, self.fix_applied, self.root_cause, self.parts_replaced,
                        self.asset_id, self.ticket_id, self.logged_date] if x
        )


# ---- model output schemas ---------------------------------------------------------------------
class ClassifyResult(BaseModel):
    matched_sop_id: str | None = Field(description="SOP ID from the catalog that covers this issue type, or null if none fits")
    confidence: float = Field(ge=0, le=1, description="If matched: confidence in the match. If null: confidence that NO catalog entry fits.")
    rationale: str
    proposed_issue_type: str | None = Field(default=None, description="Short Title Case issue-type name (<= 8 words) when matched_sop_id is null")
    fix_is_substantive: bool = Field(description="True only if the fix text contains concrete, actionable field knowledge")
    injection_suspected: bool = False


class AssessResult(BaseModel):
    verdict: Literal["no_value", "duplicate", "augments"]
    confidence: float = Field(ge=0, le=1)
    rationale: str
    new_facts: list[str] = Field(default_factory=list, description="Concise new facts (cause, fix, part, check) not already in the SOP or field experience")
    injection_suspected: bool = False


class MergeResult(BaseModel):
    merged_markdown: str
    change_summary: str


class SafetyJudgement(BaseModel):
    contradicts_safety: bool
    reason: str = ""


class NewSopDraft(BaseModel):
    issue_type_title: str = Field(description="Title Case, <= 8 words, names the issue type")
    severity: str = Field(description="P1, P2, P3 or 'Not yet established'")
    error_codes: list[str] = Field(default_factory=list, description="Only codes that appear in the ticket text")
    symptoms: str
    safety: str = Field(description="Only precautions stated in the input, otherwise 'Not yet established'")
    troubleshooting_steps: str
    resolution_verification: str
    root_causes: str
    summary: str


# ---- outcomes / audit -------------------------------------------------------------------------
class Outcome(str, Enum):
    SKIPPED = "skipped"
    AMBIGUOUS = "ambiguous"
    EXISTING_UNTOUCHED = "existing_untouched"
    NO_VALUE = "no_value"
    DUPLICATE = "duplicate"
    AUGMENTED = "augmented"
    NEW_SOP_CREATED = "new_sop_created"
    REJECTED = "rejected"
    NEEDS_APPROVAL = "needs_approval"
    ERROR = "error"


class AuditRecord(BaseModel):
    job_id: str
    ticket_id: str
    asset_id: str
    asset_type: str
    ts: str
    outcome: str = ""
    classification: dict = Field(default_factory=dict)
    verdict: str | None = None
    rationale: str = ""
    before: str | None = None
    after: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)
    guardrails: dict = Field(default_factory=lambda: {"passed": True, "failed": []})
    duration_ms: int = 0
    error: str | None = None
