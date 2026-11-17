import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_enrichment.enrichment import AuditLog, Catalog, EnrichmentEngine  # noqa: E402
from knowledge_enrichment.settings import Settings  # noqa: E402


class FakeKB:
    """In-memory stand-in for KnowledgeIndex."""

    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.neighbors: list[tuple[dict, float]] = []
        self.upserts: list[list[str]] = []

    def get_document(self, doc_id):
        return self.docs.get(doc_id)

    def filter_documents(self, odata_filter, top=1000):
        if "doc_type eq 'sop_catalog'" in odata_filter:
            return [d for d in self.docs.values() if d["doc_type"] == "sop_catalog" and d["source"] == "field_enrichment"]
        if "doc_type eq 'sop_section'" in odata_filter:
            sid = odata_filter.split("sop_id eq '")[1].rstrip("'")
            return [d for d in self.docs.values() if d["doc_type"] == "sop_section" and d["sop_id"] == sid]
        return []

    def field_catalog(self):
        return self.filter_documents("doc_type eq 'sop_catalog' and source eq 'field_enrichment'")

    def max_field_sop_number(self, family):
        nums = [int(d["sop_id"].rsplit("F", 1)[1]) for d in self.field_catalog() if d["sop_id"].startswith(f"SOP-{family}-F")]
        return max(nums, default=0)

    def semantic_neighbors(self, text, top=5):
        return self.neighbors

    def upsert_chunks(self, chunks):
        ids = [c["id"] for c in chunks]
        for c in chunks:
            self.docs[c["id"]] = dict(c)
        self.upserts.append(ids)
        return ids


class FakeLlm:
    """Returns queued model outputs by schema class name."""

    def __init__(self):
        self.queue: dict[str, list] = {}
        self.calls: list[str] = []

    def push(self, obj):
        self.queue.setdefault(type(obj).__name__, []).append(obj)

    def complete_json(self, system, user, model_cls):
        self.calls.append(model_cls.__name__)
        return self.queue[model_cls.__name__].pop(0)

    def embed(self, texts):
        return [[0.0] * 4 for _ in texts]


@pytest.fixture
def settings(tmp_path):
    return Settings(runtime_dir=tmp_path / "runtime")


@pytest.fixture
def kb():
    return FakeKB()


@pytest.fixture
def llm():
    return FakeLlm()


@pytest.fixture
def engine(settings, kb, llm):
    catalog = Catalog(settings, kb)
    return EnrichmentEngine(settings, llm, kb, catalog, AuditLog(settings.runtime_dir))
