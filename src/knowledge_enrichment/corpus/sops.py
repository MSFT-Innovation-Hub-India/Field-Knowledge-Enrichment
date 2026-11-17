"""Parse SOP markdown files. The issue type is encoded in the file name."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..settings import get_settings
from .models import CatalogEntry, Sop, SopSection

FILENAME_RE = re.compile(r"^(?P<sop_id>SOP-(?P<family>BAT|STN|GEN)-(?P<num>[A-Z0-9]+))_(?P<title>.+)\.md$")
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s*(.+?)\s*$", re.MULTILINE)
ERROR_CODE_RE = re.compile(r"\b[EW]-\d{3}\b")
SEVERITY_RE = re.compile(r"\bP[123]\b")


def load_mapping(config_dir: Path | None = None) -> dict:
    path = (config_dir or get_settings().config_dir) / "asset-type-mapping.yaml"
    if not path.exists():
        return {"defaults": {}, "overrides": {}, "sections": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def applies_to_for(sop_id: str, family: str, mapping: dict, section_key: str | None = None) -> list[str]:
    if section_key:
        override = (mapping.get("sections") or {}).get(sop_id, {}).get(section_key)
        if override:
            return list(override)
    override = (mapping.get("overrides") or {}).get(sop_id)
    if override:
        return list(override)
    return list((mapping.get("defaults") or {}).get(family, ["battery", "station"]))


def _parse_header_table(text: str) -> dict[str, str]:
    header: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if header:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("Field",) or set(cells[0]) <= {"-", " "}:
            continue
        header[cells[0]] = cells[1]
    return header


def parse_sop_text(file_name: str, text: str, mapping: dict, origin: str = "installed") -> Sop:
    m = FILENAME_RE.match(file_name)
    if not m:
        raise ValueError(f"SOP file name does not match SOP-<BAT|STN|GEN>-<id>_<Issue_Type>.md: {file_name}")
    sop_id, family = m["sop_id"], m["family"]
    issue_type = m["title"].replace("_", " ").strip()

    header = _parse_header_table(text)
    sections: list[SopSection] = []
    matches = list(SECTION_RE.finditer(text))
    for i, sm in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        number = int(sm.group(1))
        sections.append(SopSection(key=f"s{number:02d}", number=number, title=sm.group(2), body=text[sm.end():end].strip()))

    severity_text = header.get("Severity", "")
    return Sop(
        sop_id=sop_id,
        family=family,
        issue_type=issue_type,
        applies_to=applies_to_for(sop_id, family, mapping),
        error_codes=sorted(set(ERROR_CODE_RE.findall(header.get("Error codes", "")))),
        severity=severity_text or "Not yet established",
        version=header.get("Version", ""),
        sections=sections,
        header=header,
        origin=origin,
        status="field_derived_unreviewed" if origin == "field" else "official",
        raw_text=text,
    )


def load_installed_sops(sops_dir: Path | None = None, mapping: dict | None = None) -> list[Sop]:
    sops_dir = sops_dir or get_settings().sops_dir
    mapping = mapping if mapping is not None else load_mapping()
    sops: list[Sop] = []
    for path in sorted(sops_dir.glob("*.md")):
        sops.append(parse_sop_text(path.name, path.read_text(encoding="utf-8"), mapping))
    return sops


def catalog_summary(sop: Sop) -> str:
    """Deterministic one-paragraph summary (no model call): first symptoms/threshold text or header."""
    for s in sop.sections:
        if s.title.lower().startswith(("symptom", "temperature threshold", "threshold")):
            text = re.sub(r"\s+", " ", s.body).strip()
            return text[:400]
    first = sop.sections[0].body if sop.sections else ""
    return re.sub(r"\s+", " ", first).strip()[:400]


def sop_to_catalog_entry(sop: Sop) -> CatalogEntry:
    return CatalogEntry(
        sop_id=sop.sop_id,
        issue_type=sop.issue_type,
        applies_to=sop.applies_to,
        error_codes=sop.error_codes,
        severity=sop.severity,
        summary=catalog_summary(sop),
        origin=sop.origin,
    )
