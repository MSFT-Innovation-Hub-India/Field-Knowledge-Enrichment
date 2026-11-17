"""Plain data models for the corpus (SOPs, assets, catalog)."""
from __future__ import annotations

from dataclasses import dataclass, field

ASSET_TYPES = ("battery", "station")


@dataclass
class SopSection:
    key: str            # s01, s02, ...
    number: int
    title: str
    body: str           # text under the heading (without the heading line)

    @property
    def heading(self) -> str:
        return f"{self.number}. {self.title}"


@dataclass
class Sop:
    sop_id: str
    family: str                          # BAT | STN | GEN
    issue_type: str                      # derived from the file name
    applies_to: list[str]
    error_codes: list[str]
    severity: str
    version: str
    sections: list[SopSection]
    header: dict[str, str] = field(default_factory=dict)
    origin: str = "installed"            # installed | field
    status: str = "official"             # official | field_derived_unreviewed
    raw_text: str = ""

    @property
    def title(self) -> str:
        return f"{self.sop_id} · {self.issue_type}"

    def full_text(self) -> str:
        if self.raw_text:
            return self.raw_text
        return "\n\n".join(f"## {s.heading}\n{s.body}" for s in self.sections)


@dataclass
class CatalogEntry:
    sop_id: str
    issue_type: str
    applies_to: list[str]
    error_codes: list[str]
    severity: str
    summary: str
    origin: str                          # installed | field

    def as_prompt_dict(self) -> dict:
        return {
            "sop_id": self.sop_id,
            "issue_type": self.issue_type,
            "applies_to": self.applies_to,
            "error_codes": self.error_codes,
            "severity": self.severity,
            "summary": self.summary,
        }


@dataclass
class Incident:
    asset_id: str
    asset_type: str
    ticket_id: str
    date: str
    issue_code: str
    symptoms: str
    root_cause: str
    resolution: str
    status: str
    linked_sop: str
    station_id: str = ""


@dataclass
class AssetRecord:
    asset_id: str
    asset_type: str
    profile_text: str
    incidents: list[Incident]
