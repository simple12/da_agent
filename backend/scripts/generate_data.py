#!/usr/bin/env python3
"""Generate synthetic healthcare data per Phase 1 spec."""

import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import psycopg

COUNTIES = ["Alameda", "Santa Clara", "San Mateo", "Contra Costa", "San Francisco"]
AGE_GROUPS = ["0-17", "18-34", "35-49", "50-64", "65+"]
LOBS = ["Commercial", "Medicare", "Medicaid", "Exchange"]
CLAIM_STATUSES = ["PAID", "PENDING", "APPROVED"]
MONTHS = [f"2024-{m:02d}" for m in range(1, 13)]

NUM_MEMBERS = 10_000
NUM_PROVIDERS = 100
NUM_CLAIMS = 10_000


def main():
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://da_agent:da_agent@localhost:5432/da_agent"
    )
    random.seed(42)

    providers = [
        (
            f"PRV{i:05d}",
            f"Provider {i}",
            f"Group {(i % 20) + 1}",
        )
        for i in range(1, NUM_PROVIDERS + 1)
    ]

    members = [
        (
            f"MEM{i:05d}",
            random.choice(COUNTIES),
            random.choice(AGE_GROUPS),
            random.choice(LOBS),
        )
        for i in range(1, NUM_MEMBERS + 1)
    ]

    member_months = []
    for mid, _, _, _ in members:
        for mk in MONTHS:
            member_months.append((mid, mk, 1.0))

    claims = []
    start = date(2024, 1, 1)
    for i in range(1, NUM_CLAIMS + 1):
        member_id = f"MEM{random.randint(1, NUM_MEMBERS):05d}"
        provider_id = f"PRV{random.randint(1, NUM_PROVIDERS):05d}"
        service_date = start + timedelta(days=random.randint(0, 364))
        status = random.choices(CLAIM_STATUSES, weights=[70, 20, 10])[0]
        allowed = round(random.uniform(50, 5000), 2)
        if status == "PAID":
            paid = allowed
            outstanding = 0.0
        elif status == "PENDING":
            paid = 0.0
            outstanding = 0.0
        else:  # APPROVED but not fully paid
            paid = round(allowed * random.uniform(0, 0.5), 2)
            outstanding = round(allowed - paid, 2)
        claims.append(
            (
                f"CLM{i:06d}",
                member_id,
                provider_id,
                service_date,
                paid,
                allowed,
                outstanding,
                status,
            )
        )

    sql_path = Path(__file__).parent / "init_db.sql"
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text())
            cur.executemany(
                "INSERT INTO dim_provider VALUES (%s, %s, %s)",
                providers,
            )
            cur.executemany(
                "INSERT INTO dim_member VALUES (%s, %s, %s, %s)",
                members,
            )
            cur.executemany(
                "INSERT INTO fact_member_month VALUES (%s, %s, %s)",
                member_months,
            )
            cur.executemany(
                """
                INSERT INTO fact_claim
                (claim_id, member_id, provider_id, service_date,
                 paid_amount, allowed_amount, outstanding_amount, claim_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                claims,
            )
        print(
            f"Loaded {NUM_PROVIDERS} providers, {NUM_MEMBERS} members, "
            f"{len(member_months)} member-months, {NUM_CLAIMS} claims."
        )


if __name__ == "__main__":
    main()
