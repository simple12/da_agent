# Healthcare Data Analyst Agent — Phase 1 MVP

Natural-language healthcare analytics: question → LLM SQL → validator → Trino → tabular results.

## Architecture

```
React UI → FastAPI → SQL Generator (LLM/mock) → SQL Validator → Trino → Postgres (analytics catalog)
```

Postgres stores the synthetic dataset. Trino queries it through the `analytics` PostgreSQL catalog connector.

## Development

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/), Node.js 18+ (for the UI).

### Start the stack (Docker)

From the repo root:

```bash
# Postgres + Trino + API
docker compose up -d postgres trino api

# One-time (or after wiping the DB): load synthetic analytics + semantic metadata
docker compose --profile seed run --rm seed

# Rebuild API after backend code changes
docker compose up -d --build api
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Health | http://localhost:8000/health |
| Trino (from host) | http://localhost:8081 |
| Postgres (from host) | `localhost:5433` — db/user/password: `da_agent` |

Postgres uses host port **5433** when something else already occupies 5432.

**Useful Docker commands:**

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f trino
docker compose exec postgres psql -U da_agent -d da_agent
docker compose exec trino trino --execute "SHOW TABLES FROM analytics.public"
docker compose down          # stop containers
docker compose down -v       # stop + delete DB volume (requires re-seed)
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install          # first time only
npm run dev
```

Open http://localhost:5173 — Vite proxies `/ask` and `/health` to the API on port 8000.

### Verify

```bash
python3 scripts/verify_benchmarks.py http://localhost:8000
```

### Local backend (optional)

Run the API on the host while Postgres and Trino stay in Docker:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

export DATABASE_URL=postgresql://da_agent:da_agent@localhost:5433/da_agent
export QUERY_ENGINE=trino
export TRINO_HOST=localhost
export TRINO_PORT=8081
python scripts/generate_data.py
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Set `QUERY_ENGINE=postgres` to bypass Trino and query Postgres directly (useful if Trino is not running).

## LLM modes

| `LLM_PROVIDER` | Behavior |
|----------------|----------|
| `mock` (default) | Pattern-matched SQL for benchmark questions; no API key |
| `openai` | Calls OpenAI with the healthcare semantic model prompt |

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
```

## Semantic model

Tables: `fact_claim`, `fact_member_month`, `dim_member`, `dim_provider`

- **PMPM:** `SUM(paid_amount) / SUM(member_months)`
- **Outstanding:** `SUM(outstanding_amount) WHERE claim_status <> 'PAID'`
- **Pending:** `claim_status = 'PENDING'`

Only `SELECT` is allowed; DML/DDL is rejected by the validator.

## Deliverable example

```bash
curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is PMPM for Alameda County and stratify by age group?"}' | jq
```

Returns `question`, `sql`, and `results`.

## Verification

```bash
python3 scripts/verify_benchmarks.py http://localhost:8000
```

Covers all five Phase 1 benchmark questions from the spec.
