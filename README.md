# Field Knowledge Enrichment for Battery-Swap Operations

A proof of concept (POC) for AI-assisted battery-swap network operations using Microsoft Foundry and Azure AI Search. Operations staff raise battery or station tickets, receive SOP-grounded recommendations, and capture technicians' fixes to incrementally enrich the knowledge index.

## Contents

- [Overview](#overview)
- [How the solution works](#how-the-solution-works)
- [Codebase guide](#codebase-guide)
  - [Operator web UI](#operator-web-ui)
  - [Backend API](#backend-api)
  - [SOP advisor agent](#sop-advisor-agent)
  - [Source corpus and asset mapping](#source-corpus-and-asset-mapping)
  - [Knowledge index and model clients](#knowledge-index-and-model-clients)
  - [Knowledge enrichment pipeline](#knowledge-enrichment-pipeline)
  - [Guardrails, background jobs, and audit](#guardrails-background-jobs-and-audit)
  - [Bootstrap and maintenance tools](#bootstrap-and-maintenance-tools)
  - [Infrastructure and packaging](#infrastructure-and-packaging)
- [Configuration and prerequisites](#configuration-and-prerequisites)
- [Run locally](#run-locally)
- [Deploy an environment](#deploy-an-environment)
- [Testing and validation](#testing-and-validation)
- [Detailed documentation](#detailed-documentation)
- [Limitations and operational notes](#limitations-and-operational-notes)
- [Contributing](#contributing)
- [License](#license)

## Overview

- **Advise:** Recommend actions, safety warnings, and relevant incident history from standard operating procedures (SOPs) and asset records.
- **Learn:** Assess completed fixes for useful new knowledge, augment existing indexed SOPs, or draft an indexed SOP for a new issue type.
- **Ground:** Use Azure AI Search retrieval with a Microsoft Foundry agent, distinguishing field-derived knowledge from original SOP content.
- **Run:** React and TypeScript frontend, Python API, Azure Container Apps, and Bicep infrastructure with Microsoft Entra authentication for Azure services.

The scenario uses **Contoso Mobility**, a fictional battery-swap operator. The name is illustrative and does not imply affiliation with a real organization.

> **POC only:** Not production-ready or a substitute for approved operating and safety procedures. The demo UI/API allows anonymous access; Azure managed identities authenticate service-to-service calls, not end users. Review field-derived SOPs before operational use. See the [known limitations](docs/04-implementation-notes.md#known-limits-poc) before deployment. Do not upload confidential, personal, or production customer data.

## How the solution works

The solution has two connected runtime paths, backed by an initial corpus-loading step:

1. **Bootstrap the knowledge base:** The bootstrap tool parses packaged SOPs and asset history, creates searchable chunks and embeddings, and pushes them into one Azure AI Search index. A separate setup tool creates the Foundry advisor agent and its Search connection.
2. **Advise on a ticket:** The React UI sends the asset type, asset ID, and issue to the Python API. The API invokes the Foundry advisor, whose Azure AI Search tool retrieves relevant SOPs and incidents. The UI displays structured recommendations, warnings, history, and sources.
3. **Learn from a resolution:** The technician submits the actual fix. The API queues a background job that classifies the issue, checks whether the fix adds knowledge, validates generated content, and conditionally updates the index. The UI polls for completion.
4. **Close the loop:** A later ticket can retrieve the enriched knowledge. Original SOP files remain unchanged; learned content is stored in the index and labelled as field-derived.

The **advisor agent** answers operational questions through a Foundry Search tool. The **enrichment pipeline** is separate Python orchestration that calls the model and Search clients directly; it is not another advisor conversation.

For diagrams, component relationships, and sequences, see [system context](docs/02-solution-architecture.md#2-system-context) and [runtime flows](docs/02-solution-architecture.md#4-runtime-flows).

## Codebase guide

Start with the component you want to understand or change:

| Area | Responsibility | Start here |
|---|---|---|
| Web UI | Ticket entry, recommendations, resolution capture | [Operator web UI](#operator-web-ui) |
| API | Request validation, service wiring, HTTP endpoints | [Backend API](#backend-api) |
| Advisor | Foundry agent definition and grounded responses | [SOP advisor agent](#sop-advisor-agent) |
| Corpus | SOPs, asset records, parsing, applicability | [Source corpus and asset mapping](#source-corpus-and-asset-mapping) |
| Search and models | Index schema, chunks, embeddings, model calls | [Knowledge index and model clients](#knowledge-index-and-model-clients) |
| Learning | Classification, assessment, merging, SOP drafting | [Knowledge enrichment pipeline](#knowledge-enrichment-pipeline) |
| Runtime controls | Content checks, asynchronous jobs, audit records | [Guardrails, background jobs, and audit](#guardrails-background-jobs-and-audit) |
| CLI tools | Initial setup, inspection, cleanup, live validation | [Bootstrap and maintenance tools](#bootstrap-and-maintenance-tools) |
| Deployment | Container image, Azure resources, identities | [Infrastructure and packaging](#infrastructure-and-packaging) |

### Operator web UI

The [React frontend](src/ui) is built with TypeScript and Vite.

- [App.tsx](src/ui/src/App.tsx) owns the ticket form, suggested/overridable criticality, resolution form, request states, and enrichment-status polling.
- [RecommendationsPanel.tsx](src/ui/src/RecommendationsPanel.tsx) renders safety warnings, ordered actions, probable cause, incident history, and source labels.
- [api.ts](src/ui/src/api.ts) wraps backend requests; [types.ts](src/ui/src/types.ts) defines frontend data contracts.
- [styles.css](src/ui/src/styles.css) controls presentation; [vite.config.ts](src/ui/vite.config.ts) configures the frontend build.

The built UI is served by the Python application, so the deployed solution uses one application container rather than separate frontend and backend services.

**Details:** [UI specification](docs/03-technical-specification.md#13-ui-specification).

### Backend API

[app.py](src/knowledge_enrichment/api/app.py) creates the FastAPI application, wires the advisor, catalog, enrichment engine, job manager, and audit log, and serves the built UI. It also handles input validation, request rate limiting for recommendation/resolution submissions, and service errors.

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Application health and installed SOP count |
| `POST /api/recommendations` | Request a grounded recommendation for a ticket |
| `POST /api/tickets/{ticket_id}/resolution` | Accept a resolution and return a background job ID (`202`) |
| `GET /api/enrichment/{job_id}` | Return the neutral UI status: `checking` or `done` |
| `GET /api/audit` | List recent detailed enrichment records, when enabled |
| `GET /api/audit/{job_id}` | Inspect one enrichment record, when enabled |

**Details:** [API contract](docs/03-technical-specification.md#6-api-contract-fastapi). For implementation details, use the code as the source of truth and consult the [documented deviations](docs/04-implementation-notes.md#deviations-from-the-specifications).

### SOP advisor agent

[advisor.py](src/knowledge_enrichment/agents/advisor.py) contains the Foundry agent instructions, Search tool configuration, agent-version creation, asset-aware query construction, and invocation client. It requests vector-semantic-hybrid retrieval and validates the agent's structured response using [schemas.py](src/knowledge_enrichment/agents/schemas.py).

The instructions require retrieved evidence, appropriate battery/station applicability, source attribution, and no invented procedures. When no relevant knowledge is returned, the response explicitly indicates that rather than supplying unsupported actions.

**Details:** [Advisor agent contract](docs/03-technical-specification.md#7-advisor-agent).

### Source corpus and asset mapping

- [data/sops](data/sops) contains the seven seed SOPs, organised by issue type: battery thermal/BMS/health issues, station communications/charging/door faults, and general maintenance/power issues.
- [data/assets](data/assets) contains battery and station JSON records, including profiles and incident history.
- [asset-type-mapping.yaml](config/asset-type-mapping.yaml) defines applicability overrides, including SOPs that apply to both batteries and stations.
- [corpus/sops.py](src/knowledge_enrichment/corpus/sops.py), [corpus/assets.py](src/knowledge_enrichment/corpus/assets.py), and [corpus/models.py](src/knowledge_enrichment/corpus/models.py) turn those files into structured SOP, asset, incident, and catalog data.

These files are packaged into the application image as the base corpus. Field learning does not rewrite them. To promote reviewed knowledge into the packaged corpus, update the source files and rebuild/reload deliberately.

**Details:** [Corpus parsing](docs/03-technical-specification.md#3-corpus-parsing) and [asset-type awareness](docs/02-solution-architecture.md#3-the-single-index-and-asset-type-awareness).

### Knowledge index and model clients

The [kb package](src/knowledge_enrichment/kb) connects the corpus and learning pipeline to Azure services:

| Module | Purpose |
|---|---|
| [schema.py](src/knowledge_enrichment/kb/schema.py) | Defines the single Search index, metadata fields, HNSW vector configuration, Azure OpenAI vectorizer, and semantic ranking |
| [chunking.py](src/knowledge_enrichment/kb/chunking.py) | Creates SOP-section, catalog, asset-profile, incident, and field-experience chunks with deterministic IDs and asset/source headers |
| [search.py](src/knowledge_enrichment/kb/search.py) | Provides Search access for document lookup, retrieval, writes, counts, and cleanup |
| [llm.py](src/knowledge_enrichment/kb/llm.py) | Provides Entra-authenticated model and embedding calls |

Battery and station knowledge share one index. Applicability metadata and chunk headers preserve asset context; source metadata separates original knowledge from field enrichment. Updates are pushed from code, without a Blob Storage ingestion pipeline or Search indexer.

**Details:** [Chunking and keys](docs/03-technical-specification.md#4-chunking-and-keys) and [index design](docs/02-solution-architecture.md#3-the-single-index-and-asset-type-awareness).

### Knowledge enrichment pipeline

[pipeline.py](src/knowledge_enrichment/enrichment/pipeline.py) orchestrates learning from completed resolutions:

1. Skip trivial fixes and reject unsafe input before classification.
2. Classify the issue against the asset-appropriate catalog from [catalog.py](src/knowledge_enrichment/enrichment/catalog.py), which combines packaged and field-created SOP entries.
3. **Known issue:** Detect duplicate or low-value information; otherwise merge new facts into a consolidated field-experience document and add the incident.
4. **New issue:** Draft a field-derived SOP from the submitted evidence and create its section, catalog, and incident chunks in Search.
5. Apply content/structure checks and the configured approval gate before writing.

[prompts.py](src/knowledge_enrichment/enrichment/prompts.py) defines the classification, assessment, merge, draft, and safety-review prompts. [models.py](src/knowledge_enrichment/enrichment/models.py) defines tickets, model outputs, outcomes, and audit records.

Existing SOP enrichment can be disabled independently. With approval required, the pipeline records proposed content but does not write it; this POC has no approval UI or approve endpoint.

**Details:** [Enrichment stages and contracts](docs/03-technical-specification.md#8-enrichment-pipeline) and [resolution-to-enrichment flow](docs/02-solution-architecture.md#4-runtime-flows).

### Guardrails, background jobs, and audit

- [guardrails.py](src/knowledge_enrichment/enrichment/guardrails.py) checks for suspicious input, sensitive-data patterns, unsupported generated specifics, structure, and size/growth limits. Existing-SOP merges also receive a model-based safety-contradiction check in the pipeline. These checks reduce risk; they do not certify operational safety.
- [jobs.py](src/knowledge_enrichment/enrichment/jobs.py) runs enrichment in a thread pool and tracks in-memory job status. `done` means processing finished, not necessarily that knowledge was accepted or written.
- [audit.py](src/knowledge_enrichment/enrichment/audit.py) records detailed outcomes, rationale, guardrail results, and before/after content to structured logs and a local runtime JSONL file.

The UI intentionally hides enrichment verdicts. Use the audit endpoints or logs to distinguish duplicates, rejected content, errors, approval-required proposals, and successful writes.

**Details:** [Audit record](docs/03-technical-specification.md#9-audit-record-appruntimeauditjsonl-and-app-insights-custom-event) and [operating runbook](docs/04-implementation-notes.md#runbook).

### Bootstrap and maintenance tools

The [tools directory](tools) contains explicit developer/operator commands, separate from the running web app:

| Tool | Purpose |
|---|---|
| [bootstrap_index.py](tools/bootstrap_index.py) | Create/update the Search schema, parse the base corpus, embed it, and upload seed chunks |
| [create_agent.py](tools/create_agent.py) | Create/update the Entra-authenticated Search connection and publish an advisor agent version |
| [show_field_knowledge.py](tools/show_field_knowledge.py) | Inspect field-derived documents and index counts |
| [purge_field_knowledge.py](tools/purge_field_knowledge.py) | Remove field-derived content by SOP, ticket, or all; optionally undo the last field-experience merge |
| [e2e_enrichment.py](tools/e2e_enrichment.py) | Exercise the live enrichment loop against configured Azure resources |
| [_setup.py](tools/_setup.py) | Shared import-path setup for the CLI scripts |

**Caution:** Bootstrap with `--reset` deletes field-derived knowledge. Purge operations also change the live index. Verify your configured endpoint and index before running maintenance or live checks.

**Details:** [Bootstrap and housekeeping](docs/02-solution-architecture.md#5-bootstrap-and-housekeeping-from-the-laptop) and [runbook](docs/04-implementation-notes.md#runbook).

### Infrastructure and packaging

- [Dockerfile](Dockerfile) builds the React UI, installs the Python backend, packages the corpus/configuration, and runs the app as a non-root user.
- [infra/main.bicep](infra/main.bicep) deploys the Container App into an **existing** Container Apps environment, using an existing container registry, Search service, and Foundry resources. It configures ingress, health probes, environment variables, and a system-assigned identity.
- [infra/modules](infra/modules) assigns the app identity access to ACR, Search, and Foundry.
- [infra/params/dev.bicepparam](infra/params/dev.bicepparam) supplies the development environment's deployment parameters.
- [scripts/deploy.ps1](scripts/deploy.ps1) handles the initial identity/role bootstrap, builds the image in ACR, and deploys the application revision.
- [scripts/assign-roles.ps1](scripts/assign-roles.ps1) configures the Foundry/Search service-to-service roles.

The template pins the app to one replica because jobs and write locks are in-process. It does not provision an entire Azure platform from scratch.

**Details:** [Identity and access](docs/02-solution-architecture.md#6-identity-and-access-entra-only-no-keys), [infrastructure specification](docs/03-technical-specification.md#12-infrastructure-bicep), and [implementation deviations](docs/04-implementation-notes.md#deviations-from-the-specifications).

## Configuration and prerequisites

For local development, use Python (the container uses 3.12), Node.js/npm (the UI build image uses Node 22), and Azure CLI signed in with `az login`. Azure-backed operations require accessible Foundry project/model deployments and an Azure AI Search service, plus the required data-plane and setup permissions. Deployment additionally needs the existing ACR and Container Apps environment and permission to assign roles.

[.env.example](.env.example) is the local starting point; [settings.py](src/knowledge_enrichment/settings.py) defines the actual configuration fields and defaults. Replace the example environment's endpoints and resource names with your own.

| Configuration group | What to set |
|---|---|
| Foundry and models | `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_OPENAI_ENDPOINT`, `MODEL_DEPLOYMENT`, `EMBEDDING_DEPLOYMENT` |
| Search and advisor | `SEARCH_ENDPOINT`, `SEARCH_INDEX_NAME`, `ADVISOR_AGENT_NAME`, `SEARCH_CONNECTION_NAME` |
| Agent setup | `FOUNDRY_PROJECT_RESOURCE_ID`, `SEARCH_RESOURCE_ID`, and `SEARCH_LOCATION` for your resources |
| Learning controls | `ENRICH_EXISTING_SOPS`, `ENRICH_REQUIRE_APPROVAL`, classification/assessment confidence thresholds |
| Operations | `KE_AUDIT_API_ENABLED`, `RATE_LIMIT_PER_MINUTE`, optional Application Insights connection string |

Keep the embedding deployment and `EMBEDDING_DIMENSIONS` consistent with the index schema. Local credentials come from Entra authentication; deployed service calls use managed identities. Do not put credentials in the corpus or commit your local environment file.

**Details:** [Configuration reference](docs/03-technical-specification.md#10-configuration-environment-variables-no-secrets).

## Run locally

From the repository root, after configuring Azure resources and permissions:

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

Update the [environment parameters](infra/params/dev.bicepparam) and check the defaults in the [deployment script](scripts/deploy.ps1) and [role-assignment script](scripts/assign-roles.ps1) for your subscription and resource groups before running:

```powershell
./scripts/assign-roles.ps1                 # Foundry project MI -> Search, Search MI -> Foundry (once)
./scripts/deploy.ps1 -Env dev              # az acr build + Bicep (container app, identity, roles)
# then, once per environment: tools/bootstrap_index.py and tools/create_agent.py with that environment's .env
```
A new environment = `infra/params/<env>.bicepparam` + `SEARCH_INDEX_NAME` / `ADVISOR_AGENT_NAME` for that environment.

## Testing and validation

The [tests directory](tests) uses fake model and Search clients for local unit tests; those tests do not require live Azure resources.

| Test file | Coverage |
|---|---|
| [test_api.py](tests/test_api.py) | Health, response contracts, validation, asynchronous resolution status, and rate limiting |
| [test_corpus_and_chunking.py](tests/test_corpus_and_chunking.py) | SOP parsing, applicability, chunk IDs, and asset-type headers |
| [test_guardrails.py](tests/test_guardrails.py) | Unsafe input patterns, unsupported generated specifics, size limits, and structure checks |
| [test_pipeline.py](tests/test_pipeline.py) | Write/no-write decisions, duplicate handling, merging, new SOPs, revisions, and rejection paths |
| [conftest.py](tests/conftest.py) | Shared settings, fake model/index implementations, and engine fixtures |

Run backend tests from the repository root:

```powershell
.\.venv\Scripts\python -m pytest -q
```

Validate frontend types and the production build:

```powershell
Push-Location src\ui
npm run build
Pop-Location
```

The [live end-to-end script](tools/e2e_enrichment.py) is separate from unit tests: it calls Azure services, can incur costs, and writes field-derived content to the configured index. Use an isolated development index.

## Detailed documentation

| Document | Go here for |
|---|---|
| [Requirements specification](docs/01-requirements-specification.md) | Personas, scope, POC decisions, functional/non-functional requirements, security requirements, and acceptance criteria |
| [Solution architecture](docs/02-solution-architecture.md) | System diagrams, runtime sequences, single-index design, identity relationships, and deployment design |
| [Technical specification](docs/03-technical-specification.md) | Data formats, chunking rules, API/model contracts, pipeline stages, configuration, and test plan |
| [Implementation notes](docs/04-implementation-notes.md) | Recorded live verification, deviations from the specifications, maintenance tasks, and known limits |

The requirements and specifications capture design intent and may include planned behavior. Read the implementation notes alongside them to understand what the POC actually implements.

## Limitations and operational notes

- **Not a ticketing system:** There is no durable ticket database or production ticketing/telemetry integration.
- **Not a durable job service:** Background jobs and locks are in memory; the local audit file is ephemeral in the container.
- **Not an approval workflow:** Approval-required mode records a proposal without writing it; no approval endpoint is implemented.
- **Not end-user authenticated:** Anonymous UI/API access is a deliberate demo choice. Managed identities protect Azure service calls, not the public app routes. Audit endpoints are enabled by default and should be disabled or protected before broader exposure.
- **Not automatically production-scalable:** One replica is intentional; durable jobs, shared concurrency control, authentication, and operational hardening are needed before production use.
- **Not automatic SOP promotion:** Field-derived SOPs remain unreviewed indexed knowledge until a knowledge owner reviews and promotes them.

See [known limits](docs/04-implementation-notes.md#known-limits-poc), [requirements gaps](docs/01-requirements-specification.md#9-open-items-and-gaps), and the [operating runbook](docs/04-implementation-notes.md#runbook).

## Contributing

Open an issue to discuss a change or submit a focused pull request with a clear description. Keep examples fictional and exclude credentials, personal information, and customer-identifying content. For code changes, run the relevant pytest tests and, for UI changes, `npm run build` in `src/ui`. Documentation-only changes do not require application tests.

## License

Licensed under the [MIT License](LICENSE).
