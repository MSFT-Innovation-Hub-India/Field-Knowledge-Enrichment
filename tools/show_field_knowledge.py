"""List what is currently in the index that came from field enrichment (and total counts).

Usage: python tools/show_field_knowledge.py
"""
import _setup  # noqa: F401

from knowledge_enrichment.kb import AzureLlmClient, KnowledgeIndex
from knowledge_enrichment.settings import get_settings

s = get_settings()
kb = KnowledgeIndex(s, AzureLlmClient(s))
print(f"Index {s.search_index_name}: {kb.count()} documents; by source: {kb.counts_by('source')}")
for d in sorted(kb.filter_documents("source eq 'field_enrichment'"), key=lambda d: d["id"]):
    print(f"  {d['id']:55} {d['doc_type']:17} rev={d.get('revision')} tickets={d.get('source_tickets')} updated={d.get('updated_at')}")
