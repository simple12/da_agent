"""Canonical semantic model for SQL validation and prompts."""

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

RELATIONSHIPS = """
fact_claim.member_id = dim_member.member_id
fact_claim.provider_id = dim_provider.provider_id
fact_member_month.member_id = dim_member.member_id
"""

BUSINESS_METRICS = """
PMPM = SUM(paid_amount) / SUM(member_months)

Outstanding Claims = SUM(outstanding_amount) WHERE claim_status <> 'PAID'

Pending Claims = claim_status = 'PENDING'
"""


def _format_table_columns() -> str:
    lines = []
    for table, columns in APPROVED_TABLES.items():
        cols = ", ".join(sorted(columns))
        lines.append(f"{table} ({cols})")
    return "\n".join(lines)


TABLE_COLUMNS = _format_table_columns()

EXAMPLE_QUERIES = """
Example — PMPM by county:
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.county

Example — PMPM by age group (use dim_member.age_group; do not compute age from birth date):
SELECT dm.age_group, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.age_group
"""

SYSTEM_PROMPT = f"""You are a healthcare SQL analyst.

Available tables and columns (use ONLY these columns):

{TABLE_COLUMNS}

Relationships:

{RELATIONSHIPS}

Business Metrics:

{BUSINESS_METRICS}

Important column notes:
- dim_member.age_group is pre-populated (values like '0-17', '18-34', '35-49', '50-64', '65+'). Use it directly for age breakdowns.
- dim_member has NO date_of_birth or birth date column. Never reference date_of_birth.
- dim_member.county holds county names (e.g. 'Alameda').
- dim_member.lob is line of business.
- fact_member_month.month_key is a month string like '2024-01'.
- Use dim_provider.provider_name for provider labels in results.

{EXAMPLE_QUERIES}

Rules:

Generate PostgreSQL-compatible SQL only (not T-SQL, not MySQL).
Do not use DATEDIFF, GETDATE(), DATEADD, or other non-Postgres functions.
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
