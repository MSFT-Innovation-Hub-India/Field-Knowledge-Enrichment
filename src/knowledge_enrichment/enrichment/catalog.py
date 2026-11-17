"""Issue-type catalog = installed SOPs (install directory) + field-created SOPs (index)."""
from __future__ import annotations

import re
import threading
import time

from ..corpus import CatalogEntry, Sop, load_installed_sops, load_mapping, sop_to_catalog_entry
from ..kb import KnowledgeIndex
from ..settings import Settings


class Catalog:
    RECENT_TTL_S = 300  # bridge Search's near-real-time indexing lag for SOPs created moments ago

    def __init__(self, settings: Settings, kb: KnowledgeIndex):
        self.settings = settings
        self.kb = kb
        self.mapping = load_mapping(settings.config_dir)
        self.installed: dict[str, Sop] = {s.sop_id: s for s in load_installed_sops(settings.sops_dir, self.mapping)}
        self._recent: dict[str, tuple[float, CatalogEntry]] = {}
        self._lock = threading.Lock()
        self.version = 0  # bumped whenever a field SOP is registered

    def register_field_sop(self, entry: CatalogEntry) -> None:
        with self._lock:
            self._recent[entry.sop_id] = (time.monotonic(), entry)
            self.version += 1

    def _recent_entries(self) -> list[CatalogEntry]:
        now = time.monotonic()
        with self._lock:
            self._recent = {k: v for k, v in self._recent.items() if now - v[0] < self.RECENT_TTL_S}
            return [e for _, e in self._recent.values()]

    def next_field_number(self, family: str) -> int:
        prefix = f"SOP-{family}-F"
        recent = [int(e.sop_id[len(prefix):]) for e in self._recent_entries()
                  if e.sop_id.startswith(prefix) and e.sop_id[len(prefix):].isdigit()]
        return max([self.kb.max_field_sop_number(family), *recent]) + 1

    def entries(self, asset_type: str) -> list[CatalogEntry]:
        out = [sop_to_catalog_entry(s) for s in self.installed.values() if asset_type in s.applies_to]
        for doc in self.kb.field_catalog():
            if asset_type not in (doc.get("applies_to") or []):
                continue
            summary_match = re.search(r"^Summary:\s*(.+)$", doc.get("content", ""), re.MULTILINE)
            out.append(CatalogEntry(
                sop_id=doc["sop_id"],
                issue_type=doc.get("issue_type") or "",
                applies_to=doc.get("applies_to") or [],
                error_codes=doc.get("error_codes") or [],
                severity=doc.get("severity") or "",
                summary=(summary_match.group(1) if summary_match else "")[:400],
                origin="field",
            ))
        seen = {e.sop_id for e in out}
        out += [e for e in self._recent_entries() if e.sop_id not in seen and asset_type in e.applies_to]
        return out

    def all_titles(self, asset_type: str) -> list[str]:
        return [e.issue_type for e in self.entries(asset_type)]

    def sop_text(self, sop_id: str) -> str:
        """Base SOP text: installed file, or (for field-created SOPs) its section chunks from the index."""
        sop = self.installed.get(sop_id)
        if sop:
            return sop.full_text()
        docs = self.kb.filter_documents(f"doc_type eq 'sop_section' and sop_id eq '{sop_id}'")
        docs.sort(key=lambda d: d["id"])
        return "\n\n".join(body_of(d["content"]) for d in docs)

    def sop_meta(self, sop_id: str, asset_type: str) -> tuple[str, list[str], list[str], str]:
        """(issue_type, applies_to, error_codes, severity)"""
        sop = self.installed.get(sop_id)
        if sop:
            return sop.issue_type, sop.applies_to, sop.error_codes, sop.severity
        for e in self.entries(asset_type):
            if e.sop_id == sop_id:
                return e.issue_type, e.applies_to, e.error_codes, e.severity
        return sop_id, [asset_type], [], ""


def body_of(content: str) -> str:
    """Strip the two-line context header from a chunk's content."""
    parts = content.split("\n\n", 1)
    return parts[1] if len(parts) == 2 else content
