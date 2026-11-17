# Field Knowledge Enrichment (POC)

A web app where operations raise battery/station tickets, a Foundry agent recommends actions from an Azure AI Search knowledge index, and technicians' actual fixes are assessed and, when they add value, written to the index incrementally. A fix for an issue type with no SOP creates a new SOP in the index.

**Deployed (dev):** https://ke-dev-app.whitemoss-1ee70859.southindia.azurecontainerapps.io (anonymous, managed identity, no keys)

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
