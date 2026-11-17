"""FastAPI app: API routes + the built React UI served as static files (anonymous, POC)."""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from ..agents.schemas import CamelModel, Recommendation
from ..enrichment import AuditLog, Catalog, EnrichmentEngine, JobManager, Ticket
from ..settings import Settings, get_settings

log = logging.getLogger(__name__)


@dataclass
class Services:
    settings: Settings
    advisor: object          # AdvisorClient (or a fake in tests)
    jobs: JobManager
    audit: AuditLog
    catalog: Catalog


def build_services(settings: Settings) -> Services:
    from ..agents import AdvisorClient
    from ..kb import AzureLlmClient, KnowledgeIndex

    llm = AzureLlmClient(settings)
    kb = KnowledgeIndex(settings, llm)
    catalog = Catalog(settings, kb)
    audit = AuditLog(settings.runtime_dir)
    engine = EnrichmentEngine(settings, llm, kb, catalog, audit)
    return Services(settings, AdvisorClient(settings), JobManager(engine), audit, catalog)


# ---- request models ---------------------------------------------------------------------------
class RecommendationRequest(CamelModel):
    asset_id: str = Field(min_length=1, max_length=64)
    asset_type: Literal["battery", "station"]
    ticket_id: str = Field(min_length=1, max_length=64)
    issue: str = Field(min_length=1, max_length=2000)
    logged_date: str = Field(default="", max_length=32)


class ResolutionRequest(CamelModel):
    asset_id: str = Field(min_length=1, max_length=64)
    asset_type: Literal["battery", "station"]
    issue: str = Field(min_length=1, max_length=2000)
    logged_date: str = Field(default="", max_length=32)
    criticality: Literal["urgent", "priority", "normal"] | None = None
    fix_applied: str = Field(min_length=1, max_length=4000)
    root_cause: str = Field(default="", max_length=1000)
    parts_replaced: str = Field(default="", max_length=500)
    time_to_resolve_hours: float | None = Field(default=None, ge=0, le=10000)
    technician: str = Field(default="", max_length=100)


class JobAccepted(CamelModel):
    job_id: str
    status: str


class JobStatus(CamelModel):
    status: Literal["checking", "done"]


# ---- rate limiting ----------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.monotonic()
        window = [t for t in self._hits[key] if now - t < 60]
        if len(window) >= self.per_minute:
            self._hits[key] = window
            raise HTTPException(429, "Too many requests, please slow down.")
        window.append(now)
        self._hits[key] = window


def create_app(services: Services | None = None) -> FastAPI:
    settings = services.settings if services else get_settings()
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        for noisy in ("azure", "httpx", "openai", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
    if settings.applicationinsights_connection_string and services is None:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor(connection_string=settings.applicationinsights_connection_string)

    app = FastAPI(title="Field Knowledge Enrichment", version="1.0")
    app.state.services = services or build_services(settings)
    limiter = RateLimiter(settings.rate_limit_per_minute)

    def svc(request: Request) -> Services:
        return request.app.state.services

    def limit(request: Request) -> None:
        fwd = request.headers.get("x-forwarded-for", "")
        limiter.check(fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown"))

    @app.get("/healthz")
    def healthz(s: Services = Depends(svc)):
        return {"status": "ok", "installedSops": len(s.catalog.installed)}

    @app.post("/api/recommendations", response_model=Recommendation, dependencies=[Depends(limit)])
    def recommendations(body: RecommendationRequest, s: Services = Depends(svc)):
        try:
            return s.advisor.recommend(body.asset_type, body.asset_id, body.ticket_id, body.issue)
        except Exception as exc:
            log.exception("Advisor failed for %s", body.ticket_id)
            raise HTTPException(502, "The recommendation service is unavailable. Please try again.") from exc

    @app.post("/api/tickets/{ticket_id}/resolution", response_model=JobAccepted, status_code=202, dependencies=[Depends(limit)])
    def resolution(ticket_id: str, body: ResolutionRequest, s: Services = Depends(svc)):
        ticket = Ticket(
            ticket_id=ticket_id, asset_id=body.asset_id, asset_type=body.asset_type, issue=body.issue,
            logged_date=body.logged_date, criticality=body.criticality, fix_applied=body.fix_applied,
            root_cause=body.root_cause, parts_replaced=body.parts_replaced,
            time_to_resolve_hours=body.time_to_resolve_hours, technician=body.technician,
        )
        return JobAccepted(job_id=s.jobs.submit(ticket), status="checking")

    @app.get("/api/enrichment/{job_id}", response_model=JobStatus)
    def enrichment_status(job_id: str, s: Services = Depends(svc)):
        status = s.jobs.status(job_id)
        if status is None:
            raise HTTPException(404, "Unknown job")
        return JobStatus(status=status)

    @app.get("/api/audit")
    def audit_list(limit: int = 50, s: Services = Depends(svc)):
        if not s.settings.ke_audit_api_enabled:
            raise HTTPException(404)
        return s.audit.list(min(max(limit, 1), 200))

    @app.get("/api/audit/{job_id}")
    def audit_get(job_id: str, s: Services = Depends(svc)):
        if not s.settings.ke_audit_api_enabled:
            raise HTTPException(404)
        rec = s.audit.get(job_id)
        if rec is None:
            raise HTTPException(404, "Unknown job")
        return rec

    if settings.ui_dist_dir.exists():
        app.mount("/", StaticFiles(directory=settings.ui_dist_dir, html=True), name="ui")
    return app
