"""Response schema shared by the advisor agent and the API (camelCase on the wire)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Action(CamelModel):
    order: int
    text: str
    sop_id: str | None = None
    section: str | None = None


class HistoryItem(CamelModel):
    ticket_id: str | None = None
    asset_id: str | None = None
    date: str | None = None
    summary: str = ""
    resolution: str = ""


class Source(CamelModel):
    sop_id: str | None = None
    title: str | None = None
    section: str | None = None
    origin: Literal["seed", "field_enrichment"] = "seed"


class CriticalitySuggestion(CamelModel):
    suggested: Literal["urgent", "priority", "normal"] = "normal"
    basis: str = ""


class Recommendation(CamelModel):
    ticket_id: str = ""
    criticality: CriticalitySuggestion = Field(default_factory=CriticalitySuggestion)
    probable_cause: str = ""
    recommended_actions: list[Action] = Field(default_factory=list)
    safety_warnings: list[str] = Field(default_factory=list)
    past_history: list[HistoryItem] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    no_relevant_knowledge: bool = False
