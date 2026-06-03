#!/usr/bin/env python3
"""Seed Phase 2 semantic metadata from Phase 1 canonical definitions."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

# Allow imports when run as a script from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
    "fact_member_month": {"member_id", "month_key", "member_months"},
    "dim_member": {"member_id", "county", "age_group", "lob"},
    "dim_provider": {"provider_id", "provider_name", "provider_group"},
}

TABLE_DESCRIPTIONS: dict[str, str] = {
    "fact_claim": "Healthcare claims fact table",
    "fact_member_month": "Member-month eligibility and membership volume",
    "dim_member": "Member demographics and geography",
    "dim_provider": "Provider directory",
}

COLUMN_NOTES: dict[tuple[str, str], str] = {
    ("dim_member", "age_group"): "Pre-populated age band (0-17, 18-34, 35-49, 50-64, 65+)",
    ("dim_member", "county"): "County name (e.g. Alameda)",
    ("dim_member", "lob"): "Line of business",
    ("fact_member_month", "month_key"): "Month string YYYY-MM",
    ("dim_provider", "provider_name"): "Provider display label for results",
    ("fact_claim", "claim_status"): "PAID, PENDING, or APPROVED",
}

METRICS: list[tuple[str, str, str, str, str]] = [
    (
        "PMPM",
        "Per member per month paid amount",
        "SUM(paid_amount) / SUM(member_months)",
        "ratio",
        "Finance",
    ),
    (
        "OUTSTANDING_CLAIMS",
        "Total outstanding claim dollars for non-paid claims",
        "SUM(outstanding_amount) WHERE claim_status <> 'PAID'",
        "sum",
        "Finance",
    ),
    (
        "PENDING_CLAIMS",
        "Count of claims in pending status",
        "COUNT(*) WHERE claim_status = 'PENDING'",
        "count",
        "Operations",
    ),
    (
        "CLAIMS_BY_STATUS",
        "Claim volume grouped by claim status",
        "COUNT(*) GROUP BY claim_status",
        "count",
        "Operations",
    ),
    (
        "MEMBER_COUNT",
        "Distinct enrolled members",
        "COUNT(DISTINCT member_id)",
        "count",
        "Membership",
    ),
]

DIMENSIONS: list[tuple[str, str, str, str, list[str]]] = [
    ("county", "dim_member", "county", "Member county", ["counties"]),
    ("age_group", "dim_member", "age_group", "Pre-populated age band", ["age", "age group"]),
    ("lob", "dim_member", "lob", "Line of business", ["line of business"]),
    (
        "provider_group",
        "dim_provider",
        "provider_group",
        "Provider group",
        ["provider group"],
    ),
    (
        "provider_name",
        "dim_provider",
        "provider_name",
        "Provider display name",
        ["provider"],
    ),
    ("month", "fact_member_month", "month_key", "Calendar month YYYY-MM", ["monthly"]),
    (
        "claim_status",
        "fact_claim",
        "claim_status",
        "Claim status PAID/PENDING/APPROVED",
        ["status"],
    ),
]

JOINS: list[tuple[str, str, str, str]] = [
    (
        "fact_claim",
        "dim_member",
        "fact_claim.member_id = dim_member.member_id",
        "INNER",
    ),
    (
        "fact_claim",
        "dim_provider",
        "fact_claim.provider_id = dim_provider.provider_id",
        "INNER",
    ),
    (
        "fact_member_month",
        "dim_member",
        "fact_member_month.member_id = dim_member.member_id",
        "INNER",
    ),
]

SAMPLE_QUERIES: list[tuple[str, str, str | None, str]] = [
    (
        r"pmpm.*alameda.*age",
        """
SELECT dm.age_group, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
WHERE dm.county = 'Alameda'
GROUP BY dm.age_group
""".strip(),
        "PMPM",
        "PMPM for Alameda County by age group",
    ),
    (
        r"pmpm.*alameda",
        """
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
WHERE dm.county = 'Alameda'
GROUP BY dm.county
""".strip(),
        "PMPM",
        "PMPM for Alameda County",
    ),
    (
        r"pmpm.*by\s+county",
        """
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.county
""".strip(),
        "PMPM",
        "PMPM by county",
    ),
    (
        r"pmpm.*by\s+age",
        """
SELECT dm.age_group, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.age_group
""".strip(),
        "PMPM",
        "PMPM by age group",
    ),
    (
        r"pmpm.*by\s+lob",
        """
SELECT dm.lob, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.lob
""".strip(),
        "PMPM",
        "PMPM by line of business",
    ),
    (
        r"pmpm.*by\s+month",
        """
SELECT fmm.month_key, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY fmm.month_key
ORDER BY fmm.month_key
""".strip(),
        "PMPM",
        "PMPM monthly trend",
    ),
    (
        r"outstanding.*(provider|by\s+provider)",
        """
SELECT dp.provider_name, SUM(fc.outstanding_amount) AS outstanding_claims
FROM fact_claim fc
JOIN dim_provider dp ON fc.provider_id = dp.provider_id
WHERE fc.claim_status <> 'PAID'
GROUP BY dp.provider_name
""".strip(),
        "OUTSTANDING_CLAIMS",
        "Outstanding claims by provider",
    ),
    (
        r"(pending\s+payment|pending.*claim|claim.*pending)",
        """
SELECT COUNT(*) AS pending_claims_count
FROM fact_claim
WHERE claim_status = 'PENDING'
""".strip(),
        "PENDING_CLAIMS",
        "Pending claims count",
    ),
    (
        r"pmpm.*provider\s+group|provider\s+group.*pmpm",
        """
SELECT dp.provider_group, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
JOIN dim_provider dp ON fc.provider_id = dp.provider_id
GROUP BY dp.provider_group
""".strip(),
        "PMPM",
        "PMPM by provider group",
    ),
    (
        r"pmpm.*(county.*lob|lob.*county)",
        """
SELECT dm.county, dm.lob, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.county, dm.lob
""".strip(),
        "PMPM",
        "PMPM by county and LOB",
    ),
    (
        r"pmpm.*santa\s+clara",
        """
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
WHERE dm.county = 'Santa Clara'
GROUP BY dm.county
""".strip(),
        "PMPM",
        "PMPM for Santa Clara County",
    ),
    (
        r"pmpm.*san\s+francisco",
        """
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
WHERE dm.county = 'San Francisco'
GROUP BY dm.county
""".strip(),
        "PMPM",
        "PMPM for San Francisco County",
    ),
    (
        r"pending.*by\s+county|pending\s+claims?\s+by\s+county",
        """
SELECT dm.county, COUNT(*) AS pending_claims_count
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
WHERE fc.claim_status = 'PENDING'
GROUP BY dm.county
""".strip(),
        "PENDING_CLAIMS",
        "Pending claims by county",
    ),
    (
        r"claims?\s+by\s+status|claim\s+count\s+by\s+status",
        """
SELECT fc.claim_status, COUNT(*) AS claim_count
FROM fact_claim fc
GROUP BY fc.claim_status
""".strip(),
        "CLAIMS_BY_STATUS",
        "Claims by status",
    ),
    (
        r"members?\s+by\s+county|member\s+count\s+by\s+county",
        """
SELECT dm.county, COUNT(DISTINCT dm.member_id) AS member_count
FROM dim_member dm
GROUP BY dm.county
""".strip(),
        "MEMBER_COUNT",
        "Members by county",
    ),
    (
        r"members?\s+by\s+lob|member\s+count\s+by\s+lob",
        """
SELECT dm.lob, COUNT(DISTINCT dm.member_id) AS member_count
FROM dim_member dm
GROUP BY dm.lob
""".strip(),
        "MEMBER_COUNT",
        "Members by LOB",
    ),
    (
        r"(claim\s+volume\s+by\s+provider|claim\s+count\s+by\s+provider|provider\s+claim\s+volume|claims?\s+per\s+provider)",
        """
SELECT dp.provider_name, COUNT(*) AS claim_count
FROM fact_claim fc
JOIN dim_provider dp ON fc.provider_id = dp.provider_id
GROUP BY dp.provider_name
""".strip(),
        "CLAIMS_BY_STATUS",
        "Provider claim volume",
    ),
    (
        r"outstanding.*provider\s+group",
        """
SELECT dp.provider_group, SUM(fc.outstanding_amount) AS outstanding_claims
FROM fact_claim fc
JOIN dim_provider dp ON fc.provider_id = dp.provider_id
WHERE fc.claim_status <> 'PAID'
GROUP BY dp.provider_group
""".strip(),
        "OUTSTANDING_CLAIMS",
        "Outstanding claims by provider group",
    ),
]


def main() -> None:
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://da_agent:da_agent@localhost:5432/da_agent"
    )
    sql_path = Path(__file__).parent / "init_semantic.sql"

    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())

            cur.executemany(
                """
                INSERT INTO semantic.metrics
                (metric_name, metric_definition, metric_formula, aggregation_type, business_owner)
                VALUES (%s, %s, %s, %s, %s)
                """,
                METRICS,
            )

            cur.executemany(
                """
                INSERT INTO semantic.dimensions
                (dimension_name, table_name, column_name, description, aliases)
                VALUES (%s, %s, %s, %s, %s)
                """,
                DIMENSIONS,
            )

            for table_name, columns in APPROVED_TABLES.items():
                cur.execute(
                    """
                    INSERT INTO semantic.tables (table_name, description)
                    VALUES (%s, %s)
                    """,
                    (table_name, TABLE_DESCRIPTIONS.get(table_name, "")),
                )
                for column_name in sorted(columns):
                    cur.execute(
                        """
                        INSERT INTO semantic.table_columns
                        (table_name, column_name, description)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            table_name,
                            column_name,
                            COLUMN_NOTES.get((table_name, column_name), ""),
                        ),
                    )

            cur.executemany(
                """
                INSERT INTO semantic.joins
                (source_table, target_table, join_condition, join_type)
                VALUES (%s, %s, %s, %s)
                """,
                JOINS,
            )

            cur.executemany(
                """
                INSERT INTO semantic.sample_queries
                (question_pattern, sql_template, metric_name, description)
                VALUES (%s, %s, %s, %s)
                """,
                SAMPLE_QUERIES,
            )

            cur.execute("SELECT COUNT(*) FROM semantic.metrics")
            metric_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM semantic.dimensions")
            dimension_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM semantic.tables")
            table_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM semantic.table_columns")
            column_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM semantic.joins")
            join_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM semantic.sample_queries")
            sample_count = cur.fetchone()[0]

    print(
        "Seeded semantic metadata: "
        f"{metric_count} metrics, {dimension_count} dimensions, "
        f"{table_count} tables, {column_count} columns, "
        f"{join_count} joins, {sample_count} sample queries."
    )


if __name__ == "__main__":
    main()
