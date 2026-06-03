"""SQL validation constants and dialect rules.

Table/column allowlists for validation remain here until Sprint 2.5
loads them from the semantic metadata repository.
"""

from __future__ import annotations

APPROVED_TABLES: dict[str, set[str]] = {
    "fact_claim": {
        "claim_id",
        "member_id",
        "provider_id",
        "service_date",
        "paid_amount",
        "allowed_amount",
        "outstanding_amount",
        "claim_status",
    },
    "fact_member_month": {
        "member_id",
        "month_key",
        "member_months",
    },
    "dim_member": {
        "member_id",
        "county",
        "age_group",
        "lob",
    },
    "dim_provider": {
        "provider_id",
        "provider_name",
        "provider_group",
    },
}

SQL_DIALECT_RULES = """
Generate Trino SQL (ANSI SQL compatible with the Trino query engine).
Use unqualified table names (e.g. fact_claim, not catalog.schema.fact_claim).
Do not use T-SQL, MySQL, or PostgreSQL-only functions (DATEDIFF, GETDATE(), DATEADD, etc.).
Return SQL only with no markdown fences or explanation.
Never generate DDL.
Never generate DML.
Only use the approved schema and columns listed above.
Use consistent table aliases (e.g. fc, dm, fmm, dp) and define every alias in FROM/JOIN.
For PMPM metrics, join fact_claim to dim_member and fact_member_month as shown in the examples.
"""

FORBIDDEN_KEYWORDS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
        "CALL",
        "MERGE",
        "REPLACE",
    }
)

# Metric → base tables required beyond dimension tables (prompt builder).
METRIC_BASE_TABLES: dict[str, set[str]] = {
    "PMPM": {"fact_claim", "fact_member_month", "dim_member"},
    "OUTSTANDING_CLAIMS": {"fact_claim", "dim_provider"},
    "PENDING_CLAIMS": {"fact_claim"},
    "CLAIMS_BY_STATUS": {"fact_claim"},
    "MEMBER_COUNT": {"dim_member"},
}
