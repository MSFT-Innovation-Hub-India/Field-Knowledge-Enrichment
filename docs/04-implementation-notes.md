# Implementation Notes

What was built, where it differs from the specifications, and the operating runbook.

## Verified in the live environment
| Acceptance criterion | Result |
|---|---|
| 1 Bootstrap from the laptop | 73 chunks loaded (39 SOP sections, 7 SOP catalog, 19 incidents, 8 asset profiles); 56 tagged `station`, 31 `battery` (BAT-001/002 carry both) |
| 2 Asset-type awareness | Battery 61 C ticket -> SOP-BAT-001 battery fault steps. Station door ticket -> SOP-STN-003 only. A station ticket about a battery-only BMS issue, and a battery ticket about a station touchscreen, both returned `noRelevantKnowledge` |
| 3 Recommendations | Safety, ordered actions, probable cause, past history, sources, suggested criticality |
| 4 Duplicate fix | `duplicate`, no index write |
| 5 Augmenting fix (existing type) | Merged into `<SOP>__field`, base SOP untouched |
| 6 New issue type | New SOP in the index only (`SOP-BAT-F001`, `SOP-STN-F001`) |
| 7 No duplicate SOP | Second ticket matched the new SOP |
| 8 Closed loop | A similar ticket retrieved the field-derived SOP, labelled `field_enrichment` |
| 9 Keyless | No key anywhere in code, image or app settings; all calls use managed identity / `az login` |
| 10 Multi-env | Environment-specific values are in `infra/params/<env>.bicepparam` and env vars |

Tests: `pytest` runs 30 unit tests. `tools/e2e_enrichment.py` runs the live scenarios against the dev index.

## Deviations from the specifications
| Topic | Spec | As built |
|---|---|---|
| Role name | "Azure AI User" | The role is now named **Foundry User** (same role ID `53ca6127-...`). The Container App identity also gets **Cognitive Services OpenAI User** on the Foundry account. |
| Agent name | `sop-advisor` | `sop-advisor-<env>` (one agent per environment, one agent overall per environment). |
| Project connection | Created through the SDK | The Foundry SDK only lists/gets connections, so `tools/create_agent.py` creates the Entra (AAD) connection `ke-search-entra` through ARM. |
| Search key auth (SEC-07) | Disable `disableLocalAuth` after validation | **Not changed.** `ai-search-vector-001` is shared and existing agents in this project use an API-key connection to it. Disabling keys would break them. Do it only when those are migrated. |
| New-SOP race | Single in-process lock | Plus a short-lived write-through catalog cache (5 min) and a re-check under the new-SOP lock. Search is near-real-time, so an SOP created seconds earlier was not yet visible and a second ticket created a duplicate SOP. Found and fixed during live testing. |
| Approval switch (FR-39) | Queue for approval | `ENRICH_REQUIRE_APPROVAL=true` stops before writing and records the proposed content in the audit entry (outcome `needs_approval`). There is no approve endpoint in the POC (the UI is anonymous). |
| Cosine shortcut | Optional | Implemented (`ENRICH_DUPLICATE_COSINE`, default 0.92). |
| Citation markers | not mentioned | The Foundry Search tool appends markers such as `【4:0†source】` to answers; they are stripped before the response is validated. |
| No-knowledge answers | not mentioned | When `noRelevantKnowledge` is true, the backend clears any stray actions/history and suggests "priority". An SOP with severity "Not yet established" also yields "priority". |
| Logging | Application Insights | Structured JSON audit lines go to stdout (Container Apps Log Analytics). The App Insights connection string is an optional parameter; not created in this POC. |

## Runbook
| Task | Command |
|---|---|
| Reload the corpus after editing `data/` | Rebuild the image (`deploy.ps1`), then `tools/bootstrap_index.py` |
| See what enrichment did | `GET /api/audit` (read-only; in-memory and `/app/runtime/audit.jsonl`, lost on restart) or Container Apps logs (`enrichment_audit`) |
| Remove field-derived content | `tools/purge_field_knowledge.py --all` / `--sop-id X` / `--ticket T` |
| Undo the last Field-experience merge for an SOP | `tools/purge_field_knowledge.py --sop-id X --undo-last` |
| Refresh the agent after changing its instructions | `tools/create_agent.py` (creates a new agent version) |
| Reset everything field-derived and re-seed | `tools/bootstrap_index.py --reset` |

## Known limits (POC)
- Tickets, background jobs and the local audit file are in memory/ephemeral; an app restart loses in-flight jobs.
- The Container App is pinned to one replica; two replicas would break in-process locking.
- The free semantic ranker plan allows 1,000 queries per month.
- Field-created SOPs are labelled "Field-derived - not yet reviewed" and should be reviewed by a knowledge owner before promotion into `data/sops`.
