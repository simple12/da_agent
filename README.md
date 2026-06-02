# Healthcare Data Analyst Agent — Phase 1 MVP

Natural-language healthcare analytics: question → LLM SQL → validator → Postgres → tabular results.

## Architecture

```
React UI → FastAPI → SQL Generator (LLM/mock) → SQL Validator → Postgres
```

## Quick start (Docker)

```bash
# Start Postgres + API
docker compose up -d postgres api

# Load synthetic data (10k claims, 10k members, 100 providers)
docker compose --profile seed run --rm seed

# Run verification suite
python3 scripts/verify_benchmarks.py
```

API: http://localhost:8000  
Health: http://localhost:8000/health

Postgres is exposed on **5433** (not 5432) when local Postgres already uses 5432.

## Local development

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# With Docker Postgres running:
export DATABASE_URL=postgresql://da_agent:da_agent@localhost:5432/da_agent
python scripts/generate_data.py
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/ask` to the API.

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
