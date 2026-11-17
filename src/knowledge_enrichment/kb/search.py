"""Azure AI Search access (Entra only) and index writes with embeddings."""
from __future__ import annotations

import logging
from typing import Iterable

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

from ..settings import Settings
from .llm import LlmClient, get_credential

log = logging.getLogger(__name__)

SELECT_FIELDS = [
    "id", "doc_type", "title", "content", "applies_to", "sop_id", "issue_type", "section",
    "error_codes", "severity", "asset_id", "source", "sop_status", "revision", "source_tickets",
    "previous_content", "updated_at",
]


class KnowledgeIndex:
    def __init__(self, settings: Settings, llm: LlmClient):
        self.settings = settings
        self.llm = llm
        self._client = SearchClient(settings.search_endpoint, settings.search_index_name, get_credential())

    # ---- reads ---------------------------------------------------------------------------------
    def get_document(self, doc_id: str) -> dict | None:
        try:
            return self._client.get_document(key=doc_id)
        except Exception as exc:  # ResourceNotFoundError
            if "404" in str(exc) or "ResourceNotFound" in type(exc).__name__ or "not found" in str(exc).lower():
                return None
            raise

    def filter_documents(self, odata_filter: str, top: int = 1000) -> list[dict]:
        results = self._client.search(search_text="*", filter=odata_filter, select=[f for f in SELECT_FIELDS if f != "previous_content"], top=top)
        return [dict(r) for r in results]

    def field_catalog(self) -> list[dict]:
        """sop_catalog documents for field-created SOPs."""
        return self.filter_documents("doc_type eq 'sop_catalog' and source eq 'field_enrichment'")

    def max_field_sop_number(self, family: str) -> int:
        docs = self.filter_documents("doc_type eq 'sop_catalog' and source eq 'field_enrichment'", top=500)
        best = 0
        prefix = f"SOP-{family}-F"
        for d in docs:
            sid = d.get("sop_id") or ""
            if sid.startswith(prefix) and sid[len(prefix):].isdigit():
                best = max(best, int(sid[len(prefix):]))
        return best

    def semantic_neighbors(self, text: str, top: int = 5) -> list[tuple[dict, float]]:
        """Vector-only neighbours of a text with cosine similarity.

        For cosine-metric HNSW, Search reports @search.score = (1 + cosine) / 2.
        """
        from azure.search.documents.models import VectorizedQuery

        vector = self.llm.embed([text])[0]
        results = self._client.search(
            search_text=None,
            vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=top, fields="content_vector")],
            select=["id", "doc_type", "sop_id", "content"],
            top=top,
        )
        return [(dict(r), 2 * float(r["@search.score"]) - 1) for r in results]

    def count(self) -> int:
        return self._client.get_document_count()

    # ---- writes --------------------------------------------------------------------------------
    def upsert_chunks(self, chunks: list[dict]) -> list[str]:
        """Embed and merge_or_upload chunks. Idempotent because chunk ids are deterministic."""
        if not chunks:
            return []
        vectors = self.llm.embed([c["content"] for c in chunks])
        docs = []
        for chunk, vector in zip(chunks, vectors):
            doc = dict(chunk)
            doc["content_vector"] = vector
            docs.append({k: v for k, v in doc.items() if v is not None})
        for i in range(0, len(docs), 100):
            results = self._client.merge_or_upload_documents(documents=docs[i:i + 100])
            failed = [r.key for r in results if not r.succeeded]
            if failed:
                raise RuntimeError(f"Index write failed for: {failed}")
        return [c["id"] for c in chunks]

    def delete_ids(self, ids: Iterable[str]) -> int:
        ids = list(ids)
        for i in range(0, len(ids), 100):
            self._client.delete_documents(documents=[{"id": x} for x in ids[i:i + 100]])
        return len(ids)

    def counts_by(self, field: str) -> dict[str, int]:
        results = self._client.search(search_text="*", facets=[f"{field},count:50"], top=0)
        facets = results.get_facets() or {}
        return {f["value"]: f["count"] for f in facets.get(field, [])}


def index_client(settings: Settings) -> SearchIndexClient:
    return SearchIndexClient(settings.search_endpoint, get_credential())
