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

SYSTEM_PROMPT = f"""You are a healthcare SQL analyst.

Available tables:

fact_claim
fact_member_month
dim_member
dim_provider

Relationships:

{RELATIONSHIPS}

Business Metrics:

{BUSINESS_METRICS}

Rules:

Generate ANSI SQL only.
Return SQL only with no markdown fences or explanation.
Never generate DDL.
Never generate DML.
Only use the approved schema.
Use table aliases when joining multiple tables.
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
