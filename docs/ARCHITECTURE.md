# Architecture

Current implementation on `main` (Phase 1 MVP + Phase 2 semantic layer).

## System overview

```mermaid
flowchart TB
    subgraph Client["Client layer"]
        UI["React UI :5173\nVite dev server"]
    end

    subgraph API["FastAPI — da_agent-api :8000"]
        direction TB
        Routes["REST routes\n/ask · /analyze · /prompt · /health\n/metrics · /dimensions · /joins · /tables"]
        QA["Question Analyzer\nrules + metadata"]
        MS["Metadata Service"]
        SR["Semantic Repository\npsycopg"]
        PB["Prompt Builder\ndynamic system prompt"]
        SG["SQL Generator\nmock | OpenAI"]
        SV["SQL Validator\njoin graph · allowlists · intent checks"]
        QE["Query Executor\nTrino client | Postgres fallback"]
        Routes --> QA
        QA --> MS
        MS --> SR
        QA --> PB
        PB --> MS
        QA --> SG
        SG --> PB
        SG --> SV
        SV --> MS
        SV --> QE
    end

    subgraph Engine["Query engine"]
        Trino["Trino :8081\ntrinodb/trino"]
        Cat["analytics catalog\nPostgreSQL connector"]
        Trino --> Cat
    end

    subgraph Data["Postgres :5433 — da_agent"]
        Public["public schema\nfact_claim · fact_member_month\ndim_member · dim_provider"]
        Semantic["semantic schema\nmetrics · dimensions · tables\njoins · sample_queries · table_columns"]
    end

    subgraph External["Optional"]
        OpenAI["OpenAI API\ngpt-4o-mini"]
    end

    UI -->|"POST /ask\nGET /analyze · /prompt"| Routes
    SR --> Semantic
    Cat --> Public
    QE --> Trino
    QE -.->|"QUERY_ENGINE=postgres"| Public
    SG -.->|"LLM_PROVIDER=openai"| OpenAI
```

## Request flow (`POST /ask`)

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant API as FastAPI
    participant QA as Question Analyzer
    participant Meta as Metadata DB
    participant PB as Prompt Builder
    participant LLM as Mock / OpenAI
    participant Val as SQL Validator
    participant Trino as Trino
    participant PG as Postgres public

    User->>UI: Natural language question
    UI->>API: POST /ask { question }

    API->>QA: analyze(question)
    QA->>Meta: load metrics, dimensions, joins
    alt Unknown / ambiguous
        QA-->>API: QuestionAnalysisError
        API-->>UI: 400 { error, message, options? }
    end

    API->>PB: build(intent)
    PB->>Meta: metric, dims, tables, joins, samples
    PB-->>API: focused system prompt

    API->>LLM: generate SQL
    alt mock mode
        LLM->>Meta: match sample_queries regex
    else openai mode
        LLM->>LLM: chat completion
    end
    LLM-->>API: SQL string

    API->>Val: validate(sql, intent)
    Val->>Meta: approved tables/columns, join graph
    alt validation fail
        Val-->>API: SQLValidationError
        API-->>UI: 400 { error, message }
    end

    API->>Trino: execute SQL
    Trino->>PG: federated query via analytics catalog
    PG-->>Trino: rows
    Trino-->>API: results

    API-->>UI: { question, sql, results }
    UI-->>User: table + SQL preview
```

## Semantic metadata model

```mermaid
erDiagram
    METRICS ||--o{ SAMPLE_QUERIES : "metric_name"
    TABLES ||--o{ TABLE_COLUMNS : "table_name"

    METRICS {
        string metric_name PK
        string metric_formula
        string metric_definition
    }
    DIMENSIONS {
        string dimension_name PK
        string table_name
        string column_name
    }
    TABLES {
        string table_name PK
    }
    TABLE_COLUMNS {
        string table_name FK
        string column_name
    }
    JOINS {
        string source_table
        string target_table
        string join_condition
    }
    SAMPLE_QUERIES {
        string question_pattern
        string sql_template
    }

    FACT_CLAIM ||--o{ DIM_MEMBER : member_id
    FACT_CLAIM ||--o{ DIM_PROVIDER : provider_id
    FACT_MEMBER_MONTH ||--o{ DIM_MEMBER : member_id
```

## Docker deployment

```mermaid
flowchart LR
    subgraph compose["docker compose"]
        FE["frontend\nnpm run dev on host"]
        API2["api :8000"]
        TR["trino :8081"]
        PG2["postgres :5433"]
        SEED["seed profile\ngenerate_data + seed_semantic"]
    end

    FE --> API2
    API2 --> TR
    API2 --> PG2
    TR --> PG2
    SEED --> PG2
```

## Component map

| Layer | Key paths |
|-------|-----------|
| UI | `frontend/src/App.tsx` |
| API entry | `backend/app/main.py` |
| Question analyzer | `backend/app/services/question_analyzer.py` |
| Metadata | `backend/app/services/metadata_service.py`, `backend/app/repositories/semantic_repo.py` |
| Prompt builder | `backend/app/services/prompt_builder.py` |
| SQL generator | `backend/app/services/sql_generator.py` |
| SQL validator | `backend/app/services/sql_validator.py`, `backend/app/services/join_graph.py` |
| Query executor | `backend/app/services/query_executor.py` |
| Analytics seed | `backend/scripts/generate_data.py`, `backend/scripts/init_db.sql` |
| Semantic seed | `backend/scripts/seed_semantic.py`, `backend/scripts/init_semantic.sql` |
| Trino catalog | `trino/catalog/analytics.properties` |
| Infra | `docker-compose.yml` |
| Smoke tests | `scripts/verify_benchmarks.py` |
| Regression | `scripts/run_regression.py`, `tests/regression/` |

## Structured error codes

| Code | Stage |
|------|--------|
| `UNKNOWN_METRIC` | Question analyzer |
| `UNKNOWN_DIMENSION` | Question analyzer |
| `AMBIGUOUS_DIMENSION` | Question analyzer (UI offers dimension options) |
| `GENERATION_ERROR` | SQL generator |
| `INVALID_JOIN_PATH` | SQL validator |
| `METRIC_MISMATCH` | SQL validator |
| `DIMENSION_MISMATCH` | SQL validator |
| `VALIDATION_ERROR` | SQL validator (general) |
| `EXECUTION_ERROR` | Query executor |

## Related docs

- [README.md](../README.md) — setup and API usage
- [PHASE1_CHECKLIST.md](../PHASE1_CHECKLIST.md) — Phase 1 MVP status
- [PHASE2_CHECKLIST.md](../PHASE2_CHECKLIST.md) — Phase 2 semantic layer status
