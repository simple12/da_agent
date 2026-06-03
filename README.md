# Healthcare Data Analyst Agent

Natural-language healthcare analytics: question → metadata-driven SQL → Trino → tabular results.

Phase 1 delivered the end-to-end MVP. Phase 2 adds a **structured semantic layer** (Postgres metadata), question analysis, dynamic prompts, and a 53-case regression suite.

## Architecture

```
React UI → FastAPI → Question Analyzer → Metadata Service → Prompt Builder → LLM/mock → SQL Validator → Trino → Postgres
```

**Diagrams:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (system overview, sequence flow, metadata ER model, Docker layout).

| Layer | Role |
|-------|------|
| **Postgres** | Analytics data (`public`) + semantic metadata (`semantic` schema) |
| **Trino** | Query engine via `analytics` catalog (PostgreSQL connector) |
| **Metadata** | Metrics, dimensions, joins, sample queries — no business rules in code prompts |
| **Analyzer** | Extracts metric, dimensions, filters; rejects ambiguous/unknown requests |
| **Validator** | SELECT-only, metadata allowlists, join-path + intent alignment checks |

## Development

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/), Node.js 18+ (for the UI).

### Start the stack (Docker)

From the repo root:

```bash
# Postgres + Trino + API
docker compose up -d postgres trino api

# One-time (or after wiping the DB): analytics data + semantic metadata
docker compose --profile seed run --rm seed

# Rebuild API after backend code changes
docker compose up -d --build api
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Health | http://localhost:8000/health |
| Trino UI | http://localhost:8081 |
| Frontend | http://localhost:5173 (after `npm run dev`) |
| Postgres (host) | `localhost:5433` — user/password/db: `da_agent` |

Postgres uses host port **5433** when port 5432 is already in use.

**Useful commands:**

```bash
docker compose ps
docker compose logs -f api
docker compose exec postgres psql -U da_agent -d da_agent -c '\dt semantic.*'
docker compose down          # stop
docker compose down -v       # stop + wipe DB (re-seed required)
```

### Frontend

```bash
cd frontend
npm install          # first time
npm run dev
```

Open http://localhost:5173. The UI shows structured errors (e.g. ambiguous dimensions with clickable options).

### Verify

```bash
# Phase 1 smoke (5 cases)
python3 scripts/verify_benchmarks.py http://localhost:8000

# Phase 2 regression (53 cases — execution, accuracy, resolution, latency)
python3 scripts/run_regression.py http://localhost:8000
```

Regression targets (mock mode, last run): **100%** execution, accuracy, metric/dimension resolution; max latency under 10s.

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ask` | Question → SQL → results |
| `GET` | `/analyze?question=...` | Parsed intent (metric, dimensions, filters) |
| `GET` | `/prompt?question=...` | Intent + metadata-driven system prompt |
| `GET` | `/health` | Stack status + semantic metadata readiness |
| `GET` | `/metrics`, `/metrics/{name}` | Semantic metric definitions |
| `GET` | `/dimensions`, `/dimensions/{name}` | Dimension → table/column mapping |
| `GET` | `/joins` | Approved join paths |
| `GET` | `/tables` | Tables and columns from metadata |

**Example:**

```bash
curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is PMPM for Alameda County and stratify by age group?"}' | jq
```

**Structured error example:**

```bash
curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Show PMPM by group."}' | jq
# → AMBIGUOUS_DIMENSION with options: provider_group, age_group, county, lob
```

### Local backend (optional)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

export DATABASE_URL=postgresql://da_agent:da_agent@localhost:5433/da_agent
export QUERY_ENGINE=trino
export TRINO_HOST=localhost
export TRINO_PORT=8081
python scripts/generate_data.py && python scripts/seed_semantic.py
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Set `QUERY_ENGINE=postgres` to query Postgres directly without Trino.

## LLM modes

| `LLM_PROVIDER` | Behavior |
|----------------|----------|
| `mock` (default) | SQL from `semantic.sample_queries` patterns + metadata validation |
| `openai` | Dynamic prompt built from metadata + parsed intent |

```bash
# In backend/.env or docker-compose
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

Live LLM accuracy is not scored by the regression suite (mock mode). Re-run with `openai` for LLM validation.

## Semantic model (metadata-driven)

Stored in Postgres schema `semantic` (seeded by `backend/scripts/seed_semantic.py`):

| Entity | Examples |
|--------|----------|
| Metrics | PMPM, OUTSTANDING_CLAIMS, PENDING_CLAIMS, CLAIMS_BY_STATUS, MEMBER_COUNT |
| Dimensions | county, age_group, lob, provider_group, provider_name, month, claim_status |
| Tables | fact_claim, fact_member_month, dim_member, dim_provider |

Business definitions live in the database, not in application prompt strings.

## Project layout

```
backend/app/
  services/     question_analyzer, metadata_service, prompt_builder, sql_generator, sql_validator
  repositories/ semantic_repo
  routes/       metadata REST
backend/scripts/  init_semantic.sql, seed_semantic.py, generate_data.py
tests/regression/ cases/*.json, report.py
scripts/        verify_benchmarks.py, run_regression.py
frontend/       React UI
```

## Phase checklists

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system diagrams (Mermaid)
- [PHASE1_CHECKLIST.md](PHASE1_CHECKLIST.md) — MVP / Trino integration
- [PHASE2_CHECKLIST.md](PHASE2_CHECKLIST.md) — Semantic layer + regression (Sprints 2.1–2.8)

## Out of scope

GraphQL, RAG/embeddings, agent memory, dashboards, multi-agent workflows, and data write-back remain out of scope per the Phase 2 spec.
