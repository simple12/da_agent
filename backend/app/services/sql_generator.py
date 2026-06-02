from __future__ import annotations

import re
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.schema import SYSTEM_PROMPT

# Deterministic SQL for benchmark questions when llm_provider=mock
_MOCK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"pmpm.*alameda.*age", re.I),
        """
SELECT dm.age_group, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
WHERE dm.county = 'Alameda'
GROUP BY dm.age_group
""".strip(),
    ),
    (
        re.compile(r"pmpm.*alameda", re.I),
        """
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
WHERE dm.county = 'Alameda'
GROUP BY dm.county
""".strip(),
    ),
    (
        re.compile(r"pmpm.*by\s+county", re.I),
        """
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.county
""".strip(),
    ),
    (
        re.compile(r"pmpm.*by\s+age", re.I),
        """
SELECT dm.age_group, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.age_group
""".strip(),
    ),
    (
        re.compile(r"pmpm.*by\s+lob", re.I),
        """
SELECT dm.lob, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY dm.lob
""".strip(),
    ),
    (
        re.compile(r"pmpm.*by\s+month", re.I),
        """
SELECT fmm.month_key, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
GROUP BY fmm.month_key
ORDER BY fmm.month_key
""".strip(),
    ),
    (
        re.compile(r"outstanding.*(provider|by\s+provider)", re.I),
        """
SELECT dp.provider_name, SUM(fc.outstanding_amount) AS outstanding_claims
FROM fact_claim fc
JOIN dim_provider dp ON fc.provider_id = dp.provider_id
WHERE fc.claim_status <> 'PAID'
GROUP BY dp.provider_name
""".strip(),
    ),
    (
        re.compile(r"(pending\s+payment|pending.*claim|claim.*pending)", re.I),
        """
SELECT COUNT(*) AS pending_claims_count
FROM fact_claim
WHERE claim_status = 'PENDING'
""".strip(),
    ),
]


def _strip_sql_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text.rstrip(";")


def _mock_sql(question: str) -> Optional[str]:
    for pattern, sql in _MOCK_PATTERNS:
        if pattern.search(question):
            return sql
    return None


def generate_sql(question: str) -> str:
    mock = _mock_sql(question)
    if mock and settings.llm_provider == "mock":
        return mock

    if settings.llm_provider == "mock":
        raise ValueError(
            "No mock SQL template for this question. Set LLM_PROVIDER=openai and OPENAI_API_KEY."
        )

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content or ""
    return _strip_sql_fences(content)
