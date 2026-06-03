# Phase 2 Checklist

Status against the [Phase 2 spec](Phase%202%20%E2%80%93%20Structured%20Semantic%20Layer%20and%20SQL%20Reliability.docx). Last reviewed against commit on `main`.

**Overall:** **Phase 2 complete (Sprints 2.1–2.8).** Metadata-driven SQL generation, structured errors, and 53-case regression suite meet acceptance targets in mock mode. See [README.md](README.md) for run instructions.

**Last verified:** mock regression 53/53 pass — execution 100%, accuracy 100%, metric/dimension resolution 100%, max latency under 10s.

**Target architecture:**

```
React UI → API → Question Analyzer → Metadata Service → Prompt Builder → LLM → SQL Validator+ → Trino → Postgres
```

---

## Core deliverables

| Item | Status | Target / notes |
|------|--------|----------------|
| Semantic metadata schema (`metrics`, `dimensions`, `tables`, `joins`, `sample_queries`) | ✅ | `backend/scripts/init_semantic.sql` — includes `table_columns` |
| Seed metadata from current Phase 1 definitions | ✅ | `seed_semantic.py` — 5 metrics, 7 dims, 4 tables, 18 cols, 3 joins, **18** sample queries |
| Pydantic models for semantic entities | ✅ | `backend/app/models/semantic.py` |
| Metadata service (internal lookup API) | ✅ | `metadata_service.py`, `semantic_repo.py` |
| Metadata REST endpoints | ✅ | `GET /metrics`, `/metrics/{name}`, `/dimensions`, `/dimensions/{name}`, `/joins`, `/tables` |
| Question analyzer (metric, dimension, filter extraction) | ✅ | `backend/app/services/question_analyzer.py` |
| Ambiguity & unsupported-request detection | ✅ | `UNKNOWN_METRIC`, `UNKNOWN_DIMENSION`, `AMBIGUOUS_DIMENSION` |
| Wire into `POST /ask` before SQL generation | ✅ | Analyzer runs first; `GET /analyze` for debugging |
| Dynamic prompt builder (metadata-driven, not static prompt) | ✅ | `backend/app/services/prompt_builder.py` |
| Refactor SQL generator to use intent + built prompt | ✅ | `generate_sql(question, intent)`; OpenAI uses dynamic prompt |
| Slim `schema.py` to validation / dialect rules only | ✅ | Dialect rules + `METRIC_BASE_TABLES`; allowlists from metadata |
| Enhanced SQL validator (metric, dimension, join path) | ✅ | `sql_validator.py`, `join_graph.py` |
| Structured error responses | ✅ | Backend + React UI with dimension option picker |
| Regression test framework (50+ cases) | ✅ | `tests/regression/cases/*.json` (53 cases) |
| Automated accuracy reporting | ✅ | `scripts/run_regression.py`, `tests/regression/report.py` |
| Phase 1 smoke tests still pass | ✅ | `scripts/verify_benchmarks.py` (5 cases) |

---

## Acceptance criteria

| Criterion | Target | Status | Notes |
|-----------|--------|--------|-------|
| SQL execution success | ≥ 95% | ✅ | 100% (mock mode, 53 cases) |
| SQL accuracy (benchmark suite) | ≥ 90% | ✅ | 100% pattern match |
| Metric resolution accuracy | ≥ 95% | ✅ | 100% via `/analyze` |
| Dimension resolution accuracy | ≥ 95% | ✅ | 100% via `/analyze` |
| Hallucinated tables | 0 | ✅ | Table/column allowlists loaded from semantic metadata |
| Response time (benchmark queries) | < 10s | ✅ | Regression max ~3.8s; Phase 1 smoke ~2s |
| Security (SELECT only) | 100% enforced | ✅ | Carried forward from Phase 1 |

---

## Workstreams (implementation order)

Track sprint-by-sprint; keep `verify_benchmarks.py` green after each increment.

| Sprint | Deliverable | Status | Depends on |
|--------|-------------|--------|------------|
| **2.1** | Semantic schema DDL + seed script | ✅ | — |
| **2.2** | Metadata service (internal + REST) | ✅ | 2.1 |
| **2.3** | Question analyzer (rules + ambiguity) | ✅ | 2.2 |
| **2.4** | Dynamic prompt builder + `sql_generator` refactor | ✅ | 2.2, 2.3 |
| **2.5** | Enhanced validator (join path, metric/dim) | ✅ | 2.2 |
| **2.6** | Structured errors + frontend handling | ✅ | 2.3 |
| **2.7** | 50+ regression cases + reporting | ✅ | 2.4, 2.5 |
| **2.8** | README + checklist sign-off | ✅ | all |

---

## Metadata repository

| Table | Required fields (spec) | Status | Notes |
|-------|--------------------------|--------|-------|
| `metrics` | metric_id, name, definition, formula, aggregation_type, business_owner | ✅ | PMPM, OUTSTANDING_CLAIMS, PENDING_CLAIMS, CLAIMS_BY_STATUS, MEMBER_COUNT |
| `dimensions` | dimension_id, name, table_name, column_name, description | ✅ | county, age_group, lob, provider_group, provider_name, month, claim_status |
| `tables` | table_id, name, description | ✅ | fact_claim, fact_member_month, dim_member, dim_provider |
| `table_columns` | table_name, column_name, description | ✅ | 18 columns seeded from `APPROVED_TABLES` |
| `joins` | join_id, source, target, condition, type | ✅ | fact_claim↔dim_member, fact_claim↔dim_provider, fact_member_month↔dim_member |
| `sample_queries` | query_id, question_pattern, sql_template | ✅ | 8 patterns migrated from `sql_generator.py` mock templates |

---

## Question analyzer

| Capability | Status | Notes |
|------------|--------|-------|
| Extract metric from NL question | ✅ | e.g. `"What is PMPM for Alameda County?"` → `PMPM` |
| Extract dimensions | ✅ | e.g. `["county", "age_group"]` from `by` clauses |
| Extract filters | ✅ | e.g. `{ "county": "Alameda" }` |
| Detect unsupported metrics / dimensions | ✅ | Return `UNKNOWN_METRIC` / `UNKNOWN_DIMENSION` |
| Detect ambiguous dimensions (do not guess) | ✅ | e.g. `"Show PMPM by group"` → `AMBIGUOUS_DIMENSION` + options |
| Wire into `POST /ask` before SQL generation | ✅ | `backend/app/main.py` |

---

## SQL validation enhancements

| Check | Phase 1 | Phase 2 target | Status |
|-------|---------|----------------|--------|
| SELECT only (no DML/DDL) | ✅ | ✅ | ✅ |
| Table exists | ✅ | Metadata DB as source of truth | ✅ |
| Column exists | ✅ | Metadata DB as source of truth | ✅ |
| Metric validation | — | Verify SQL aligns with resolved metric | ✅ |
| Dimension validation | — | Verify requested dims appear in SQL | ✅ |
| Join path validation | — | All referenced tables connected via `joins` graph | ✅ |
| Ambiguity detection (pre-SQL) | — | Analyzer returns structured error | ✅ |

---

## Regression test framework

| Item | Target | Status | Notes |
|------|--------|--------|-------|
| Location | `tests/regression/` | ✅ | Per spec |
| Case format | question, expected_sql_pattern, expected_result | ✅ | JSON under `tests/regression/cases/` |
| Minimum test count | 50+ | ✅ | 53 cases |
| PMPM variants | Covered | ✅ | county, age, LOB, provider group, monthly trend |
| Claims variants | Covered | ✅ | outstanding, pending, by status, by provider |
| Membership variants | Covered | ✅ | members by county, by LOB |
| Provider variants | Covered | ✅ | claim volume, outstanding claims |
| Automated report | execution %, accuracy %, resolution %, latency | ✅ | `scripts/run_regression.py` |

---

## Supported question types (must remain working)

| Question | Phase 1 mock | Metadata-driven | In regression (50+) |
|----------|--------------|-----------------|---------------------|
| What is PMPM for Alameda County? | ✅ | ✅ | ✅ |
| Show PMPM by county | ✅ | ✅ | ✅ |
| Show PMPM by age group | ✅ | ✅ | ✅ |
| Show PMPM by LOB | ✅ | ✅ | ✅ |
| Show PMPM by provider group | ✅ | ✅ | ✅ |
| Show PMPM by month | ✅ | ✅ | ✅ |
| Outstanding claims by provider | ✅ | ✅ | ✅ |
| Pending claims by county | ✅ | ✅ | ✅ |
| Claims by status | ✅ | ✅ | ✅ |
| PMPM by county and LOB (completion criterion) | ✅ | ✅ | ✅ |
| Outstanding claims by provider group (completion criterion) | ✅ | ✅ | ✅ |

---

## Completion criteria (PRD sign-off questions)

These must work **via metadata retrieval**, not hardcoded prompt definitions:

| Question | Status |
|----------|--------|
| What is PMPM for Alameda County? | ✅ |
| What is PMPM by age group? | ✅ |
| What is PMPM by county and LOB? | ✅ |
| What are outstanding claims by provider group? | ✅ |
| Show pending claims by county. | ✅ |

Additional gates:

- [x] 50+ regression tests defined and runnable
- [x] Regression report meets all acceptance targets (90% accuracy, 95% execution/resolution, 0 hallucinated tables)
- [x] Structured errors returned for ambiguous / unknown requests
- [x] `schema.py` no longer contains business metric definitions used at prompt time

---

## Architecture & stack

| Item | Status | Notes |
|------|--------|-------|
| Postgres analytics data (Phase 1) | ✅ | Unchanged |
| Trino query engine (Phase 1) | ✅ | Unchanged |
| Semantic metadata in Postgres (`semantic` schema) | ✅ | Same `da_agent` DB; seeded via `docker compose --profile seed run --rm seed` |
| Iceberg lakehouse | ➖ | Out of Phase 2 scope; Trino → Postgres catalog remains |
| LLM → SQL → Trino pipeline (no agents) | ✅ | Architecture constraint preserved |
| Mock mode driven by `sample_queries` metadata | ✅ | Regex patterns loaded from `semantic.sample_queries` |
| Live LLM default for regression scoring | ❌ | Record results for both mock and `openai` |

---

## Explicitly out of scope (must stay absent)

| Item | Status |
|------|--------|
| GraphQL, pgvector, embeddings, vector search, RAG | ✅ Not built |
| LangGraph, CrewAI, Semantic Kernel | ✅ Not built |
| Agent memory / conversational context | ✅ Not built |
| Dashboards, forecasting, root cause analysis | ✅ Not built |
| Multi-agent workflows | ✅ Not built |
| Data write-back | ✅ Not built |

---

## Structured error codes

| Code | When | Status | Example response field |
|------|------|--------|------------------------|
| `UNKNOWN_METRIC` | Metric not in metadata | ✅ | `"message": "Metric not found."` |
| `UNKNOWN_DIMENSION` | Dimension not in metadata | ✅ | |
| `AMBIGUOUS_DIMENSION` | Multiple dimension matches | ✅ | `"options": ["provider_group", "age_group", …]` |
| `INVALID_JOIN_PATH` | Tables not joinable | ✅ | Post-validator |
| `VALIDATION_ERROR` | SQL fails enhanced checks | ✅ | Includes `METRIC_MISMATCH`, `DIMENSION_MISMATCH` |
| `GENERATION_ERROR` | Mock/LLM SQL generation failed | ✅ | |
| `EXECUTION_ERROR` | Trino/Postgres query failed | ✅ | |

Successful `/ask` response shape stays unchanged: `{ question, sql, results }`.

---

## How to verify locally

**Phase 1 smoke (baseline — run now):**

```bash
docker compose up -d postgres trino api
docker compose --profile seed run --rm seed
python3 scripts/verify_benchmarks.py http://localhost:8000
```

**Phase 2 semantic verify (Sprint 2.1 — available now):**

```bash
docker compose --profile seed run --rm seed
docker compose exec postgres psql -U da_agent -d da_agent -c '\dt semantic.*'
docker compose exec postgres psql -U da_agent -d da_agent -c \
  "SELECT metric_name, metric_formula FROM semantic.metrics ORDER BY metric_name;"
```

**Metadata REST smoke (Sprint 2.2 — available now):**

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/metrics/PMPM | jq
curl -s http://localhost:8000/dimensions/county | jq
curl -s http://localhost:8000/joins | jq
curl -s http://localhost:8000/tables | jq
```

**Phase 2 regression (Sprint 2.7 — not yet implemented):**

```bash
# Full regression + report
python3 scripts/run_regression.py http://localhost:8000
```

**Completion criterion curls:**

```bash
curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is PMPM for Alameda County?"}' | jq

curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is PMPM by county and LOB?"}' | jq

curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Show pending claims by county."}' | jq
```

curl -s "http://localhost:8000/analyze?question=What%20is%20PMPM%20for%20Alameda%20County%3F" | jq
curl -s "http://localhost:8000/analyze?question=Show%20PMPM%20by%20group." | jq

curl -s "http://localhost:8000/prompt?question=Show%20PMPM%20by%20county." | jq '.prompt' -r | head -30

**Ambiguity check (Sprint 2.3 — available now):**

```bash
curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Show PMPM by group."}' | jq
# Expect: error AMBIGUOUS_DIMENSION with options, not guessed SQL
```

---

## Open design decisions

| Decision | Recommendation | Resolved |
|----------|----------------|----------|
| Question analyzer: rules-only vs hybrid LLM | Start rules-only; add LLM extraction only if regression misses 95% | ✅ Rules-only; 100% resolution in regression |
| Metadata REST: public vs internal-only | Expose read-only endpoints for debugging; `/ask` uses internal service | ✅ |
| `schema.py` during migration | Thin fallback until metadata is source of truth, then validation constants only | ✅ |
| Mock mode in Phase 2 | Drive from `sample_queries` + analyzer, not hardcoded regex | ✅ |

---

## Sign-off

Phase 2 engineering implementation is **complete**. Stakeholder sign-off pending.

| Role | Name | Date | Metadata-driven flow | Regression targets met |
|------|------|------|----------------------|------------------------|
| Engineering | (implemented) | 2026-06 | ✅ | ✅ (mock, 53 cases) |
| Product / stakeholder | | | ☐ | ☐ |

**Remaining for full LLM sign-off:** run regression with `LLM_PROVIDER=openai` and record results in this checklist.
