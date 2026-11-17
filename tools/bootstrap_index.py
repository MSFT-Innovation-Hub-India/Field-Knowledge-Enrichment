"""Create/update the knowledge index and load the packaged corpus directly into Azure AI Search.

Run from the developer machine after `az login`. Idempotent (deterministic chunk ids).
Usage: python tools/bootstrap_index.py [--reset] [--index-name NAME]
"""
import argparse

import _setup  # noqa: F401  (sets sys.path)

from knowledge_enrichment.corpus import load_assets, load_installed_sops, load_mapping, sop_to_catalog_entry
from knowledge_enrichment.kb import AzureLlmClient, KnowledgeIndex, build_index, index_client
from knowledge_enrichment.kb import chunking
from knowledge_enrichment.settings import get_settings


def build_seed_chunks(settings) -> list[dict]:
    mapping = load_mapping(settings.config_dir)
    sops = load_installed_sops(settings.sops_dir, mapping)
    titles = {s.sop_id: s.issue_type for s in sops}
    chunks: list[dict] = []
    for sop in sops:
        chunks += chunking.sop_section_chunks(sop)
        chunks.append(chunking.sop_catalog_chunk(sop, sop_to_catalog_entry(sop).summary))
    for asset in load_assets(settings.assets_dir):
        chunks.append(chunking.asset_profile_chunk(asset))
        for inc in asset.incidents:
            chunks.append(chunking.incident_chunk(inc, sop_title=titles.get(inc.linked_sop)))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="also delete field-derived (field_enrichment) chunks")
    parser.add_argument("--index-name", help="override SEARCH_INDEX_NAME")
    args = parser.parse_args()

    settings = get_settings()
    if args.index_name:
        settings = settings.model_copy(update={"search_index_name": args.index_name})

    print(f"Search: {settings.search_endpoint}  index: {settings.search_index_name}")
    index_client(settings).create_or_update_index(build_index(settings))
    print("Index schema created/updated.")

    kb = KnowledgeIndex(settings, AzureLlmClient(settings))
    if args.reset:
        stale = [d["id"] for d in kb.filter_documents("source eq 'field_enrichment'")]
        print(f"--reset: deleted {kb.delete_ids(stale)} field-derived chunks")

    chunks = build_seed_chunks(settings)
    kb.upsert_chunks(chunks)
    print(f"Uploaded {len(chunks)} seed chunks.")

    import time
    time.sleep(2)
    print("Documents in index:", kb.count())
    print("By doc_type:", kb.counts_by("doc_type"))
    print("By source:", kb.counts_by("source"))
    print("By applies_to:", kb.counts_by("applies_to"))


if __name__ == "__main__":
    main()
