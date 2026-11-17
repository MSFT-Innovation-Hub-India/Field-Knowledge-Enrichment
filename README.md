# Field Knowledge Enrichment for Battery-Swap Operations

A proof of concept (POC) for AI-assisted battery-swap network operations using Microsoft Foundry and Azure AI Search. Operations staff raise battery or station tickets, receive SOP-grounded recommendations, and capture technicians' fixes to incrementally enrich the knowledge index.

## Overview

- **Advise:** Recommend actions, safety warnings, and relevant incident history from standard operating procedures (SOPs) and asset records.
- **Learn:** Assess completed fixes for useful new knowledge, augment existing indexed SOPs, or draft an indexed SOP for a new issue type.
- **Ground:** Use Azure AI Search retrieval with a Microsoft Foundry agent, distinguishing field-derived knowledge from original SOP content.
- **Run:** React and TypeScript frontend, Python API, Azure Container Apps, and Bicep infrastructure with Microsoft Entra authentication for Azure services.

The scenario uses **Contoso Mobility**, a fictional battery-swap operator. The name is illustrative and does not imply affiliation with a real organization.

> **POC only:** Not production-ready or a substitute for approved operating and safety procedures. The demo UI/API allows anonymous access; Azure managed identities authenticate service-to-service calls, not end users. Review field-derived SOPs before operational use. See the [known limitations](docs/04-implementation-notes.md#known-limits-poc) before deployment. Do not upload confidential, personal, or production customer data.

## Documents
| Doc | Purpose |
|---|---|
| [docs/01-requirements-specification.md](docs/01-requirements-specification.md) | Requirements, POC decisions, security, acceptance criteria |
| [docs/02-solution-architecture.md](docs/02-solution-architecture.md) | Architecture, diagrams, index design, flows, identity/roles |
| [docs/03-technical-specification.md](docs/03-technical-specification.md) | Parsing rules, index schema, API, agent, pipeline, guardrails, config |
| [docs/04-implementation-notes.md](docs/04-implementation-notes.md) | What was built, deviations from the spec, runbook |

## Layout
| Path | Contents |
|---|---|
| `data/sops`, `data/assets` | Corpus packaged into the app's install directory (issue type is in the SOP file name) |
| `config/asset-type-mapping.yaml` | Which SOPs apply to battery / station |
| `src/knowledge_enrichment` | Python backend: `api`, `corpus`, `agents`, `enrichment`, `kb` |
| `src/ui` | React (Vite + TypeScript) UI |
| `tools` | CLI: `bootstrap_index`, `create_agent`, `purge_field_knowledge`, `e2e_enrichment` |
| `infra`, `scripts` | Bicep, `deploy.ps1` (az acr build + deployment), `assign-roles.ps1` |
| `tests` | pytest unit tests (fake model and index) |

## Run locally (az login required; Entra auth, no keys)
```powershell
python -m venv .venv; .\.venv\Scripts\pip install -r requirements-dev.txt
copy .env.example .env            # adjust names; add FOUNDRY_PROJECT_RESOURCE_ID and SEARCH_RESOURCE_ID for create_agent
.\.venv\Scripts\python tools\bootstrap_index.py      # create index + load corpus from data/
.\.venv\Scripts\python tools\create_agent.py         # Entra Search connection + advisor agent
cd src\ui; npm install; npm run build; cd ..\..; Copy-Item src\ui\dist ui-dist -Recurse
$env:PYTHONPATH="src"; .\.venv\Scripts\python -m uvicorn knowledge_enrichment.api.app:create_app --factory --port 8000
.\.venv\Scripts\python -m pytest -q
```

## Deploy an environment
```powershell
./scripts/assign-roles.ps1                 # Foundry project MI -> Search, Search MI -> Foundry (once)
./scripts/deploy.ps1 -Env dev              # az acr build + Bicep (container app, identity, roles)
# then, once per environment: tools/bootstrap_index.py and tools/create_agent.py with that environment's .env
```
A new environment = `infra/params/<env>.bicepparam` + `SEARCH_INDEX_NAME` / `ADVISOR_AGENT_NAME` for that environment.

## Contributing

Open an issue to discuss a change or submit a focused pull request with a clear description. Keep examples fictional and exclude credentials, personal information, and customer-identifying content. For code changes, run the relevant pytest tests and, for UI changes, `npm run build` in `src/ui`. Documentation-only changes do not require application tests.

## License

Licensed under the [MIT License](LICENSE).
