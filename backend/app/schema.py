"""SQL dialect rules and shared constants."""

from __future__ import annotations

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

METRIC_BASE_TABLES: dict[str, set[str]] = {
    "PMPM": {"fact_claim", "fact_member_month", "dim_member"},
    "OUTSTANDING_CLAIMS": {"fact_claim", "dim_provider"},
    "PENDING_CLAIMS": {"fact_claim"},
    "CLAIMS_BY_STATUS": {"fact_claim"},
    "MEMBER_COUNT": {"dim_member"},
}
