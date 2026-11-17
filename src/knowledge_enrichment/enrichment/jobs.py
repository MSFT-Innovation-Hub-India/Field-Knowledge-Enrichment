"""In-memory background jobs. Only 'checking' / 'done' are exposed to the UI (FR-22)."""
from __future__ import annotations

import logging
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from .models import Ticket
from .pipeline import EnrichmentEngine

log = logging.getLogger(__name__)


class JobManager:
    def __init__(self, engine: EnrichmentEngine, max_workers: int = 2, keep: int = 1000):
        self.engine = engine
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="enrich")
        self._status: OrderedDict[str, str] = OrderedDict()
        self._keep = keep

    def submit(self, ticket: Ticket) -> str:
        job_id = uuid.uuid4().hex[:12]
        self._status[job_id] = "checking"
        while len(self._status) > self._keep:
            self._status.popitem(last=False)
        future = self._pool.submit(self.engine.process, job_id, ticket)
        future.add_done_callback(lambda f, j=job_id: self._finish(j, f))
        return job_id

    def _finish(self, job_id: str, future) -> None:
        if future.exception():
            log.error("Enrichment job %s crashed: %s", job_id, future.exception())
        self._status[job_id] = "done"

    def status(self, job_id: str) -> str | None:
        return self._status.get(job_id)
