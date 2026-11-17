# Requirements Specification — Field Knowledge Enrichment (POC)

| | |
|---|---|
| Status | **Draft v2 — for review.** No application code has been built yet. |
| Customer / domain | Sun Mobility — battery-swap network operations |
| Companions | [02-solution-architecture.md](./02-solution-architecture.md), [03-technical-specification.md](./03-technical-specification.md) |

## 1. Purpose

Operations staff raise tickets for battery and station issues. Today the know-how lives in SOP documents and in technicians' heads. This POC delivers a small web application that:

1. **Advises** — for a new ticket, shows recommended actions, safety warnings and past history, retrieved from an Azure AI Search index by a Microsoft Foundry agent.
2. **Learns** — when the technician records the fix that actually worked, the application asks a Foundry model whether the fix adds value to the existing corpus and, if so, enriches the Azure AI Search index so the next similar ticket benefits.

## 2. Scope and POC decisions

### In scope
- React UI, backend API on Azure Container Apps, Foundry agent with Azure AI Search knowledge tool.
- **One** Azure AI Search index for all knowledge (batteries and stations together).
- Asset type (**Battery** or **Station**) is stated in the natural-language query; retrieval must return results appropriate to that type.
- Corpus (SOPs and asset records) **packaged inside the application's install directory** (container image) and read at runtime by the backend.
- Incremental enrichment written **directly to the AI Search index** (push from code; no blob, no indexer).
- Issue-type detection against SOP names; a **new SOP is created for a new issue type** (index only).
- Keyless access: Microsoft Entra / managed identities for the Container App and the Foundry agent.
- Multi-environment deployment using `az acr build` (no local Docker).

### Explicit POC decisions (from the customer)
| # | Decision |
|---|---|
| P1 | **No Azure Blob Storage and no Cosmos DB** (they require VNet/private IP). The corpus lives in the application directory; the AI Search index is the only durable store of enriched knowledge. |
| P2 | **No separate indexes** per asset type. One index; the query text states Battery or Station. |
| P3 | **Dock is out of scope.** |
| P4 | **SOPs are organised by issue type**; the issue type is the SOP name. A new issue type ⇒ a new SOP document. |
| P5 | A newly created SOP is added to the **index only**, not to the application install directory. |
| P6 | **Anonymous** access to the Container App. |
| P7 | VNet / private endpoints deferred. Blob storage will be introduced at the next stage. |

### Out of scope
End-user sign-in, real ticketing-system/telemetry integration, durable ticket storage, mobile/offline, multi-language, VNet.

## 3. Users

| Persona | Needs |
|---|---|
| **Operations person** | Creates a ticket for an asset and reads recommendations and past history. |
| **Field technician** | Records the fix actually applied; benefits from the knowledge base improving from field experience. |
| **Knowledge owner** (secondary) | Reviews what was added or changed and why; can purge field-derived content. |

## 4. Functional requirements

### 4.1 Ticket entry and recommendations

| ID | Requirement |
|---|---|
| FR-01 | UI captures **Asset ID**, **Asset type** (Battery / Station), **Ticket ID**, **Nature of issue** (free text), **Date of issue logged**. |
| FR-02 | A **Criticality** field with **Urgent / Priority / Normal**. The agent proposes a value from the matched SOP severity (P1→Urgent, P2→Priority, P3→Normal); the user may override. |
| FR-03 | A **Recommendations** panel shows: recommended actions (ordered), safety warnings, probable cause, matched SOP(s) with version/origin, **past history** (similar incidents, including this asset's), and citations. |
| FR-04 | Recommendations are produced by the **Foundry agent** using its **Azure AI Search knowledge tool**, grounded only in retrieved content. If nothing relevant is found the panel says so. |
| FR-05 | Content learned from the field (`source=field_enrichment`) is visibly distinguished from original SOP content. |
| FR-06 | Loading and error states are shown for agent/search failures. |

### 4.2 Asset-type awareness (single index)

| ID | Requirement |
|---|---|
| FR-10 | The backend builds the natural-language query so that it **states the asset type** (e.g. "Battery issue: …"). Retrieval and the agent must return results appropriate to that type. |
| FR-11 | Every indexed chunk carries the asset type(s) it applies to — both as a filterable field and in the chunk text header — so keyword, vector and semantic ranking can all use it. |
| FR-12 | Applicability is derived from the SOP ID prefix (`BAT`→Battery, `STN`/`GEN`→Station) with explicit overrides in an editable mapping file (e.g. SOP-BAT-001 also covers station cabinet overheating, so it applies to both). |
| FR-13 | The agent is instructed to use only knowledge applicable to the stated asset type and to say when a retrieved item is for the other type. |
| FR-14 | Past history includes asset-specific incidents (same Asset ID) as well as similar fleet incidents. |

### 4.3 Capturing the actual fix

| ID | Requirement |
|---|---|
| FR-20 | A text area for **fixes actually applied** (optional: root cause, parts replaced, time to resolve, technician). |
| FR-21 | Submitting saves the ticket and returns control immediately. |
| FR-22 | After submit the UI shows only a neutral status — *"Checking whether this can enrich the knowledge base…"* then *"Done"*. Verdicts and details are not shown to the technician. |
| FR-23 | Enrichment never blocks the user. |

### 4.4 Issue-type detection and enrichment decision

| ID | Requirement |
|---|---|
| FR-30 | On submit, a Foundry model classifies the ticket against the **issue-type catalog** for that asset type. The catalog is the SOP names in the install directory **plus** field-created SOPs present in the index. |
| FR-31 | The SOP **file name encodes the issue type** (`SOP-<BAT\|STN\|GEN>-<nnn>_<Issue_Type>.md`); the catalog is built from these names and header metadata (error codes, applies-to, severity). |
| FR-32 | Skip rule: trivial fix text (too short / no actionable content) ⇒ no further model calls and no writes. |
| FR-33 | **Issue type exists** ⇒ the model assesses the fix against the SOP (install directory) and its existing field experience (index) and returns `no_value`, `duplicate`, or `augments`. `no_value` / `duplicate` ⇒ **no index write**. |
| FR-34 | `augments` ⇒ the model **merges** the new knowledge into the SOP's consolidated **Field experience** section (rewritten in context — grouping by cause and fix, de-duplicating, keeping ticket references — not a raw append). Stored in the index. The base SOP file in the install directory is not modified. *(Switch `ENRICH_EXISTING_SOPS`; see open item Q1.)* |
| FR-35 | **Issue type does not exist** ⇒ the model confirms no catalog entry fits and the fix is substantive, then **drafts a new SOP** in the house format for the Battery or Station asset type. The new SOP gets a new ID (`SOP-<BAT\|STN>-F<nnn>`), a name encoding the issue type, status "Field-derived – not yet reviewed", and is **added to the index only** (P5). |
| FR-36 | A drafted SOP contains only information supported by the ticket and technician input. It must not invent safety procedures, thresholds, part numbers or error codes. Where unknown, the section states "Not yet established". |
| FR-37 | Guardrails (structure, size, no secrets/PII, no instruction-injection, no invented specifics, no contradiction of a base-SOP safety instruction) are applied before any write; failures are rejected and audited. |
| FR-38 | A later ticket of the same new issue type matches the field-created SOP via the catalog (no duplicate SOP) and follows FR-33/34. |
| FR-39 | A configuration switch can require **human approval** before applying (default: auto-apply). |

### 4.5 Incremental index update

| ID | Requirement |
|---|---|
| FR-40 | Only the changed or new chunks are embedded (`text-embedding-3-small`) and upserted; unaffected chunks are untouched. |
| FR-41 | When a fix adds value, the resolution is also indexed as an **incident (past-history) record**: asset ID, asset type, issue, root cause, fix, date, ticket ID, SOP link. |
| FR-42 | Writes are idempotent (deterministic chunk IDs); reprocessing a ticket creates no duplicates. |
| FR-43 | Chunks carry metadata: `source` (`seed`/`field_enrichment`), `sop_id`, `issue_type`, `applies_to`, `error_codes`, `revision`, `source_tickets`, `updated_at`. |
| FR-44 | After an update, a similar new ticket retrieves the enriched content (automated end-to-end test). |
| FR-45 | Index writes use the **Container App's managed identity** (no keys). |

### 4.6 Bootstrap, audit and housekeeping

| ID | Requirement |
|---|---|
| FR-50 | A CLI run **from the developer machine** creates/updates the index schema and loads the packaged corpus (`data/sops`, `data/assets`) directly into Azure AI Search. |
| FR-51 | A CLI creates/updates the Foundry agent and its Entra-authenticated Search connection. |
| FR-52 | Bootstrap is idempotent and does not remove field-derived content unless `--reset` is used. |
| FR-53 | Every enrichment attempt is audited (ticket, catalog match, verdict, rationale, before/after, resulting chunk IDs) to structured logs (Application Insights) and a local runtime file. |
| FR-54 | A CLI can **purge field-derived content** (by SOP, ticket or all) from the index; base SOPs are always recoverable by re-running bootstrap. One-step undo of the last field-experience merge is supported (previous text stored on the chunk). |

## 5. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Performance | Recommendations ≤ 15 s p95. |
| NFR-02 | Performance | Enrichment ≤ 60 s p95; asynchronous. |
| NFR-03 | Reliability | Enrichment is retry-safe; a failed job leaves the index unchanged or consistently updated (writes are idempotent). |
| NFR-04 | Observability | Structured logs + Application Insights; correlation by ticket ID. |
| NFR-05 | Portability | All environment-specific values are configuration; none hard-coded. |
| NFR-06 | Deployability | One script per environment: `az acr build` + Bicep. |
| NFR-07 | Maintainability | Clear module separation (architecture §8). |
| NFR-08 | Cost | Small footprint; the model for classification/assessment/merge is configurable (`gpt-5.4` default). |
| NFR-09 | Concurrency | Writes for the same SOP are serialised (single replica + in-process lock). |

## 6. Security and identity

| ID | Requirement |
|---|---|
| SEC-01 | **No API keys, connection strings or secrets** in code, config, image or app settings. `DefaultAzureCredential` everywhere (`az login` locally; managed identity in Azure). |
| SEC-02 | **Container App** system-assigned managed identity searches and updates the index and calls Foundry models and the agent. |
| SEC-03 | The **Foundry agent** reaches Azure AI Search through the **Foundry project's managed identity** via an Entra-authenticated project connection. |
| SEC-04 | The **Azure AI Search** managed identity is used by the index vectorizer to call the embedding deployment. |
| SEC-05 | ACR image pull uses managed identity (`AcrPull`). |
| SEC-06 | Anonymous ingress ⇒ input size limits, rate limiting, prompt-injection-aware prompts (fix text is untrusted data), guardrails (FR-37), audit and purge (FR-53/54). |
| SEC-07 | After roles are in place, disable API-key auth on `ai-search-vector-001` (currently `disableLocalAuth=false`). |
| SEC-08 | The install-directory corpus is read-only at runtime. |

## 7. Assumptions

| # | Assumption |
|---|---|
| A1 | Region split accepted for POC: Container Apps South India, Foundry Sweden Central, AI Search Switzerland North. |
| A2 | Reuse Container Apps environment `pcdotai-agent` (RG `pcdotai-agent`) and ACR `pcdotaiagentd10b5a`. |
| A3 | Models in Foundry project `ihub-project-common`: `gpt-5.4` and `text-embedding-3-small` (confirmed deployed). |
| A4 | Deployer has Owner / User Access Administrator, so role assignments can be scripted. |
| A5 | One Container App replica (min = max = 1). |
| A6 | Corpus is small (7 SOPs, 8 asset files). |
| A7 | The install directory is part of the image: changing seed content requires a rebuild; field-derived content lives only in the index. |
| A8 | Tickets are not stored durably in the POC (held in the running process and audit log); their *knowledge* is persisted in the index when it adds value. |

## 8. Acceptance criteria

1. **Bootstrap:** from the laptop, the CLI creates the index and loads every SOP section and asset record, each tagged with the right asset type(s).
2. **Asset-type awareness:** "Battery issue: cell at 61°C while charging" returns SOP-BAT-001 content; "Station issue: slot door not locking" returns SOP-STN-003 content and no battery-only SOPs.
3. **Recommendations:** steps, safety warnings, similar past incidents and citations are shown.
4. **Duplicate fix:** a fix that restates an SOP step ⇒ verdict `duplicate`, **no index write**.
5. **Augmenting fix, existing issue type:** a fix with a new root cause or part ⇒ Field-experience section merged and indexed; base SOP file unchanged.
6. **New issue type:** a ticket for an issue with no matching SOP (e.g. a battery that fails a firmware-update handshake) ⇒ a new field-derived SOP is created **in the index only**, with a new ID and issue-type name.
7. **No duplicate SOP:** a second ticket for that same new issue type is matched to the new SOP, not a third.
8. **Closed loop:** a following ticket for the same issue shows the enriched/new content labelled as field-enriched.
9. **Keyless:** no key/secret anywhere; Search key auth disabled and the app still works.
10. **Multi-env:** a second environment deploys by changing only parameters.

## 9. Open items and gaps

**Status: all items Q1–Q9 are agreed** (Q1 explicitly; Q2–Q9 accepted as proposed on 2026-11-17). The defaults below are the baseline for the build.

| # | Topic | Proposed default |
|---|---|---|
| **Q1** | **Existing issue types — RESOLVED.** A valuable fix for an **existing** issue type enriches the index as that SOP's *Field experience* section (FR-34); the base SOP file is never changed. | Confirmed by the customer. Still switchable with `ENRICH_EXISTING_SOPS=false`. |
| **Q2** | **Asset-type precision.** With one index and no hard filter, relevance by asset type relies on the type being in the query, in each chunk's text, and in agent instructions (soft). | Accept for POC; verify with acceptance test 2. If it leaks, fall back to app-side retrieval with an `applies_to` filter, still one index. |
| **Q3** | **Durability.** Enriched knowledge survives in the index, but tickets and the local audit file are lost on restart; seed-content changes need an image rebuild. | Accept for POC; audit also goes to App Insights; durable stores arrive with blob storage. |
| **Q4** | **Applicability mapping.** Proposed: BAT-001 and BAT-002 → Battery + Station (they contain station cooling / slot-connector sections); BAT-003 → Battery; STN-001/002/003 and GEN-001 → Station. | Confirm or edit `config/asset-type-mapping.yaml`. |
| **Q5** | **Auto-apply vs approval** for LLM-created SOPs (SOPs include thermal-event safety). | Auto-apply as "Field-derived – not yet reviewed" with guardrails; approval switch available. |
| **Q6** | **Backend stack** not specified. | Python FastAPI; React + Vite served by the same container. |
| **Q7** | **Search tier limits:** semantic ranker is on the free plan (1,000 queries/month); one replica. | Fine for POC. |
| **Q8** | **Environments:** same subscription and Search service, index-name prefix per environment, separate Container App per environment? | Yes. |
| **Q9** | **Quality of new SOPs.** A new SOP can only be as good as the ticket text. | Flag as unreviewed; a knowledge owner reviews field-created SOPs before they are promoted into `data/sops` at the next stage. |
