"""Audit trail: structured log + local runtime file (ephemeral in the container, see spec A8)."""
from __future__ import annotations

import json
import logging
import threading
from collections import deque
from pathlib import Path

from .models import AuditRecord

log = logging.getLogger("ke.audit")


class AuditLog:
    def __init__(self, runtime_dir: Path, keep: int = 200):
        self.path = runtime_dir / "audit.jsonl"
        self._lock = threading.Lock()
        self._recent: deque[dict] = deque(maxlen=keep)
        try:
            runtime_dir.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                for line in self.path.read_text(encoding="utf-8").splitlines()[-keep:]:
                    self._recent.append(json.loads(line))
        except Exception:  # unreadable runtime dir must never stop the app
            log.warning("Audit file not available; using memory only", exc_info=True)

    def write(self, record: AuditRecord) -> None:
        data = record.model_dump()
        log.info("enrichment_audit %s", json.dumps(data, ensure_ascii=False))
        with self._lock:
            self._recent.append(data)
            try:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
            except OSError:
                log.warning("Could not append to audit file", exc_info=True)

    def list(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(self._recent)[-limit:][::-1]

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            return next((r for r in reversed(self._recent) if r["job_id"] == job_id), None)
