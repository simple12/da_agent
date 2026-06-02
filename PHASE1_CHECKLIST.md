# Phase 1 Checklist

Status against the [Phase 1 spec](Healthcare%20Data%20Analyst%20Agent%20MVP%20-%20Phase1.docx). Last reviewed against commit on `main`.

**Overall:** MVP / demo is **complete**. LLM-centric acceptance criteria are **partial** until OpenAI mode is exercised at scale.

---

## Core deliverables

| Item | Status | Notes |
|------|--------|-------|
| React UI → API → SQL gen → validator → DB | ✅ | `frontend/`, `backend/app/main.py` |
| Question intake (`POST /ask`) | ✅ | `{ "question": "..." }` |
| SQL generation with semantic model in prompt | ✅ | `backend/app/schema.py` |
| SQL validator (SELECT only, no DML/DDL) | ✅ | `backend/app/services/sql_validator.py` |
| Query execution + tabular results | ✅ | Postgres via `query_executor.py` |
| Response shape `{ question, sql, results }` | ✅ | No charts, explanations, or traces |
| Canonical tables & metric definitions | ✅ | 4 tables; PMPM, outstanding, pending |
| Synthetic seed data (spec minimums) | ✅ | `backend/scripts/generate_data.py` |
| Final deliverable question (Alameda PMPM by age) | ✅ | Verified via API |
| Docker Compose stack | ✅ | `docker-compose.yml` |
| Benchmark verification script (5 tests) | ✅ | `scripts/verify_benchmarks.py` |

---

## Acceptance criteria

| Criterion | Target | Status | Notes |
|-----------|--------|--------|-------|
| SQL accuracy | ≥ 80% benchmark questions | ⚠️ | 5/5 pass in **mock** mode; not measured for arbitrary NL or live LLM |
| SQL validity (executes) | ≥ 95% | ⚠️ | 5/5 execute in mock mode; no broad automated scorecard |
| Security (SELECT only) | 100% enforced | ✅ | Keyword + statement-type checks |
| End-to-end latency | < 10s | ✅ | Benchmarks ~0.01–0.09s in Docker |

---

## Architecture & stack

| Item | Status | Notes |
|------|--------|-------|
| Postgres for analytics data | ✅ | DB `da_agent`, host port `5433` |
| Trino / Iceberg | ➖ | Out of scope for this cut; Postgres substituted |
| Live LLM (default) | ⚠️ | Default `LLM_PROVIDER=mock`; OpenAI path available (`gpt-4o-mini`) |
| Column-level SQL validation | ✅ | Qualified + unqualified columns checked against `APPROVED_TABLES` |

---

## Explicitly out of scope (must stay absent)

| Item | Status |
|------|--------|
| GraphQL, vectors, embeddings, RAG | ✅ Not built |
| LangGraph, CrewAI, Semantic Kernel | ✅ Not built |
| Agent memory / conversational context | ✅ Not built |
| Dashboards, forecasting, root cause | ✅ Not built |
| Data write-back | ✅ Not built |

---

## Example question coverage

| Question type | Mock templates | In verify script |
|---------------|----------------|------------------|
| PMPM for Alameda County | ✅ | ✅ Test 1 |
| PMPM by county | ✅ | ✅ Test 2 |
| PMPM by age group | ✅ | ✅ Test 3 |
| Outstanding claims by provider | ✅ | ✅ Test 4 |
| Pending claims count | ✅ | ✅ Test 5 |
| PMPM by LOB | ✅ | ❌ |
| PMPM by month | ✅ | ❌ |
| Alameda PMPM stratified by age (deliverable) | ✅ | Manual / curl |

---

## How to verify locally

```bash
docker compose up -d postgres api
docker compose --profile seed run --rm seed
python3 scripts/verify_benchmarks.py http://localhost:8000
```

Deliverable curl:

```bash
curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is PMPM for Alameda County and stratify by age group?"}' | jq
```

---

## Recommended before calling Phase 1 “LLM-validated”

1. Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY`, rebuild API.
2. Re-run `scripts/verify_benchmarks.py` and record pass/fail.
3. Test 10+ paraphrased questions; track SQL accuracy and execution rate.
4. ~~Add column validation to `sql_validator.py` (spec requirement).~~ Done — see `backend/tests/test_sql_validator.py`

---

## Sign-off

| Role | Name | Date | Phase 1 MVP | LLM hypothesis validated |
|------|------|------|---------------|-------------------------|
| Engineering | | | ☐ | ☐ |
| Product / stakeholder | | | ☐ | ☐ |
