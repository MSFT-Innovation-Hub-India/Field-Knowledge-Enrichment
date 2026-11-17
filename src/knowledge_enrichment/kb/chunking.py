"""Turn corpus objects into index chunks (dicts without vectors).

Context header at the top of every chunk makes the asset type visible to keyword,
vector and semantic ranking (FR-11). Search keys allow only letters, digits, '_', '-', '='.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ..corpus.models import AssetRecord, Incident, Sop

MAX_CHUNK_CHARS = 4000
SOURCE_SEED = "seed"
SOURCE_FIELD = "field_enrichment"

_KEY_SAFE = re.compile(r"[^A-Za-z0-9_\-=]")


def safe_key(value: str) -> str:
    return _KEY_SAFE.sub("-", value)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def asset_label(applies_to: list[str]) -> str:
    return ", ".join(t.capitalize() for t in applies_to) or "Unknown"


def build_header(
    applies_to: list[str],
    title: str,
    section: str | None = None,
    error_codes: list[str] | None = None,
    severity: str | None = None,
    source: str = SOURCE_SEED,
    revision: int | None = None,
) -> str:
    line1 = f"Asset type: {asset_label(applies_to)} | {title}"
    if section:
        line1 += f" | Section: {section}"
    parts = []
    if error_codes:
        parts.append("Error codes: " + ", ".join(error_codes))
    if severity:
        parts.append("Severity: " + re.sub(r"\s+", " ", severity)[:120])
    label = "Field enrichment" if source == SOURCE_FIELD else "Original SOP"
    if revision:
        label += f" (rev {revision})"
    parts.append(f"Source: {label}")
    return line1 + "\n" + " | ".join(parts)


def split_text(text: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    current = ""
    for para in re.split(r"\n{2,}|\n(?=[-*\d])", text):
        if current and len(current) + len(para) + 1 > limit:
            parts.append(current)
            current = para
        else:
            current = f"{current}\n{para}" if current else para
    if current:
        parts.append(current)
    return parts


def _base_doc(**kwargs) -> dict:
    doc = {
        "id": "", "doc_type": "", "title": "", "content": "",
        "applies_to": [], "sop_id": None, "issue_type": None, "section": None,
        "error_codes": [], "severity": None, "asset_id": None,
        "source": SOURCE_SEED, "sop_status": "official", "revision": 1,
        "source_tickets": [], "previous_content": None, "updated_at": now_iso(),
    }
    doc.update(kwargs)
    return doc


def sop_section_chunks(sop: Sop, source: str = SOURCE_SEED, revision: int = 1, tickets: list[str] | None = None) -> list[dict]:
    chunks: list[dict] = []
    for section in sop.sections:
        header = build_header(sop.applies_to, sop.title, section.heading, sop.error_codes, sop.severity, source, revision if source == SOURCE_FIELD else None)
        bodies = split_text(f"## {section.heading}\n{section.body}")
        for i, body in enumerate(bodies, start=1):
            suffix = "" if len(bodies) == 1 else f"__p{i}"
            chunks.append(_base_doc(
                id=safe_key(f"{sop.sop_id}__{section.key}{suffix}"),
                doc_type="sop_section",
                title=sop.title,
                content=f"{header}\n\n{body}",
                applies_to=sop.applies_to,
                sop_id=sop.sop_id,
                issue_type=sop.issue_type,
                section=section.heading,
                error_codes=sop.error_codes,
                severity=re.sub(r"\s+", " ", sop.severity)[:200],
                source=source,
                sop_status=sop.status,
                revision=revision,
                source_tickets=tickets or [],
            ))
    return chunks


def sop_catalog_chunk(sop: Sop, summary: str, source: str = SOURCE_SEED, revision: int = 1, tickets: list[str] | None = None) -> dict:
    header = build_header(sop.applies_to, sop.title, "Catalog", sop.error_codes, sop.severity, source)
    severity_text = re.sub(r"\s+", " ", sop.severity)
    body = (
        f"Issue type: {sop.issue_type}\n"
        f"SOP ID: {sop.sop_id}\n"
        f"Applies to: {asset_label(sop.applies_to)}\n"
        f"Error codes: {', '.join(sop.error_codes) or 'None recorded'}\n"
        f"Severity: {severity_text}\n"
        f"Status: {'Field-derived, not yet reviewed' if sop.status != 'official' else 'Official SOP'}\n"
        f"Summary: {summary}"
    )
    return _base_doc(
        id=safe_key(f"{sop.sop_id}__catalog"),
        doc_type="sop_catalog",
        title=sop.title,
        content=f"{header}\n\n{body}",
        applies_to=sop.applies_to,
        sop_id=sop.sop_id,
        issue_type=sop.issue_type,
        section="Catalog",
        error_codes=sop.error_codes,
        severity=re.sub(r"\s+", " ", sop.severity)[:200],
        source=source,
        sop_status=sop.status,
        revision=revision,
        source_tickets=tickets or [],
    )


def field_experience_chunk(
    sop_id: str,
    issue_type: str,
    applies_to: list[str],
    error_codes: list[str],
    severity: str,
    markdown: str,
    revision: int,
    tickets: list[str],
    previous_content: str | None,
) -> dict:
    title = f"{sop_id} · {issue_type}"
    header = build_header(applies_to, title, "Field experience (technician-reported)", error_codes, severity, SOURCE_FIELD, revision)
    return _base_doc(
        id=safe_key(f"{sop_id}__field"),
        doc_type="field_experience",
        title=title,
        content=f"{header}\n\n{markdown}",
        applies_to=applies_to,
        sop_id=sop_id,
        issue_type=issue_type,
        section="Field experience",
        error_codes=error_codes,
        severity=re.sub(r"\s+", " ", severity)[:200],
        source=SOURCE_FIELD,
        revision=revision,
        source_tickets=tickets,
        previous_content=previous_content,
    )


def incident_chunk(inc: Incident, source: str = SOURCE_SEED, sop_title: str | None = None) -> dict:
    title = f"Incident {inc.ticket_id} on {inc.asset_id}"
    header = build_header([inc.asset_type], title, "Past incident", [inc.issue_code] if inc.issue_code else None, None, source)
    lines = [
        f"Asset ID: {inc.asset_id}",
        f"Ticket: {inc.ticket_id}",
        f"Date reported: {inc.date}",
        f"Issue code: {inc.issue_code}" if inc.issue_code else "",
        f"Station: {inc.station_id}" if inc.station_id else "",
        f"Symptoms: {inc.symptoms}",
        f"Root cause: {inc.root_cause}",
        f"Resolution: {inc.resolution}",
        f"Status: {inc.status}",
        f"Linked SOP: {inc.linked_sop}" if inc.linked_sop else "",
    ]
    body = "\n".join(line for line in lines if line)
    return _base_doc(
        id=safe_key(f"{inc.asset_id}__{inc.ticket_id}__incident"),
        doc_type="incident",
        title=title,
        content=f"{header}\n\n{body}",
        applies_to=[inc.asset_type],
        sop_id=inc.linked_sop or None,
        issue_type=sop_title,
        section="Past incident",
        error_codes=[inc.issue_code] if inc.issue_code else [],
        asset_id=inc.asset_id,
        source=source,
        source_tickets=[inc.ticket_id] if inc.ticket_id else [],
    )


def asset_profile_chunk(asset: AssetRecord) -> dict:
    title = f"Asset profile {asset.asset_id}"
    header = build_header([asset.asset_type], title, "Asset profile", None, None, SOURCE_SEED)
    return _base_doc(
        id=safe_key(f"{asset.asset_id}__profile"),
        doc_type="asset_profile",
        title=title,
        content=f"{header}\n\n{asset.profile_text}",
        applies_to=[asset.asset_type],
        section="Asset profile",
        asset_id=asset.asset_id,
        source=SOURCE_SEED,
    )
