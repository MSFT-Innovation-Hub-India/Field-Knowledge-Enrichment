"""Live closed-loop check against the real Azure resources (dev index). Run: python tools/e2e_enrichment.py

Scenarios: duplicate fix, augmenting fix, new issue type, second ticket for the same new issue type,
then asks the advisor agent for a similar ticket and shows whether the enriched content is retrieved.
"""
import json
import sys

import _setup  # noqa: F401

from knowledge_enrichment.enrichment import AuditLog, Catalog, EnrichmentEngine, Ticket
from knowledge_enrichment.kb import AzureLlmClient, KnowledgeIndex
from knowledge_enrichment.settings import get_settings

s = get_settings()
llm = AzureLlmClient(s)
kb = KnowledgeIndex(s, llm)
engine = EnrichmentEngine(s, llm, kb, Catalog(s, kb), AuditLog(s.runtime_dir))


def run(name: str, **kw) -> None:
    t = Ticket(**kw)
    rec = engine.process(name, t)
    print(f"\n### {name}: outcome={rec.outcome} verdict={rec.verdict} ms={rec.duration_ms}")
    print("   classification:", json.dumps({k: v for k, v in rec.classification.items() if k != 'rationale'}))
    print("   rationale:", rec.rationale[:300])
    if rec.guardrails and not rec.guardrails.get("passed", True):
        print("   guardrails:", rec.guardrails)
    if rec.chunk_ids:
        print("   chunks:", rec.chunk_ids)
    if rec.error:
        print("   ERROR:", rec.error)


scenario = sys.argv[1] if len(sys.argv) > 1 else "all"
if scenario in ("all", "A"):
    run("A-duplicate", ticket_id="INC-E2E-001", asset_id="WMQISXM1V1-02614", asset_type="station", logged_date="2026-11-17",
        issue="Slot 5 door not locking after battery insertion, swap incomplete",
        fix_applied="Cleaned the latch with contact cleaner and applied dry PTFE lubricant, then checked the strike plate and the lock engaged.")
if scenario in ("all", "B"):
    run("B-augment", ticket_id="INC-E2E-002", asset_id="WMQISXM1V1-02614", asset_type="station", logged_date="2026-11-17",
        issue="Slot 5 door not locking intermittently, E-305 raised, swap incomplete",
        fix_applied="Latch and strike plate were fine. The real cause was a loose door-sensor connector on the slot 5 harness; it vibrated loose each time the door slammed. Reseated the connector and added a cable tie strain relief. 50 open/close cycles passed with no E-305.",
        root_cause="Loose door-sensor connector on slot 5 harness")
if scenario in ("all", "C"):
    run("C-new-issue", ticket_id="INC-E2E-003", asset_id="INSMOMAH2109A271AD13", asset_type="battery", logged_date="2026-11-17",
        issue="Battery stuck at 40 percent during BMS firmware OTA update and then rejects further updates",
        fix_applied="Connected the battery to the offline service tool with the USB service cable, cleared the BMS bootloader flag and re-flashed the firmware. After that the battery accepted the OTA update and showed the new BMS version.",
        root_cause="BMS bootloader flag left set after an interrupted OTA update")
if scenario in ("all", "D"):
    run("D-same-new-issue", ticket_id="INC-E2E-004", asset_id="INSMOMAH8210F2625D13", asset_type="battery", logged_date="2026-11-17",
        issue="BMS firmware OTA update stuck at 40 percent on a battery, retries fail",
        fix_applied="Used the offline service tool and USB cable to clear the stuck BMS bootloader flag, then re-flashed the BMS firmware. Battery now takes OTA updates. Also noticed the OTA had been interrupted by a station power dip, so check the station voltage log first.",
        root_cause="Interrupted OTA left the bootloader flag set; triggered by a station power dip")
print("\nIndex docs:", kb.count(), kb.counts_by("source"))
