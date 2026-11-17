"""Delete field-derived chunks from the index, or undo the last Field-experience merge.

Usage:
  python tools/purge_field_knowledge.py --all
  python tools/purge_field_knowledge.py --sop-id SOP-BAT-001
  python tools/purge_field_knowledge.py --ticket INC-2026-11201
  python tools/purge_field_knowledge.py --sop-id SOP-BAT-001 --undo-last
Base (seed) content is never touched; re-run bootstrap_index.py to restore it if needed.
"""
import argparse

import _setup  # noqa: F401

from knowledge_enrichment.kb import AzureLlmClient, KnowledgeIndex
from knowledge_enrichment.kb.chunking import now_iso
from knowledge_enrichment.settings import get_settings


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--sop-id")
    g.add_argument("--ticket")
    p.add_argument("--undo-last", action="store_true", help="with --sop-id: restore previous Field-experience text")
    args = p.parse_args()

    kb = KnowledgeIndex(get_settings(), AzureLlmClient(get_settings()))

    if args.undo_last:
        if not args.sop_id:
            p.error("--undo-last requires --sop-id")
        doc = kb.get_document(f"{args.sop_id}__field")
        if not doc:
            print("No field experience chunk for", args.sop_id)
            return
        prev = doc.get("previous_content")
        if not prev:
            kb.delete_ids([doc["id"]])
            print("No previous revision: removed the field experience chunk.")
            return
        header = doc["content"].split("\n\n", 1)[0]
        doc["content"] = f"{header}\n\n{prev}"
        doc["previous_content"] = None
        doc["revision"] = max(1, int(doc.get("revision") or 1) - 1)
        doc["updated_at"] = now_iso()
        doc.pop("@search.score", None)
        kb.upsert_chunks([{k: v for k, v in doc.items() if not k.startswith("@") and k != "content_vector"}])
        print("Restored previous revision for", args.sop_id)
        return

    if args.all:
        flt = "source eq 'field_enrichment'"
    elif args.sop_id:
        flt = f"source eq 'field_enrichment' and sop_id eq '{args.sop_id}'"
    else:
        flt = f"source eq 'field_enrichment' and source_tickets/any(t: t eq '{args.ticket}')"
    ids = [d["id"] for d in kb.filter_documents(flt)]
    print(f"Deleted {kb.delete_ids(ids)} chunks")


if __name__ == "__main__":
    main()
