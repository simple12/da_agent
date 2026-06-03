from __future__ import annotations

import pytest

from app.models.question_intent import QuestionIntent
from app.models.semantic import Join
from app.services.join_graph import JoinGraph
from app.services.metadata_service import MetadataService
from app.services.sql_validator import SQLValidationError, validate_sql

VALID_PMPM = """
SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
FROM fact_claim fc
JOIN dim_member dm ON fc.member_id = dm.member_id
JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
WHERE dm.county = 'Alameda'
GROUP BY dm.county
"""


@pytest.fixture
def metadata() -> MetadataService:
    return MetadataService()


def test_join_graph_connected():
    joins = [
        Join(
            join_id=1,
            source_table="fact_claim",
            target_table="dim_member",
            join_condition="fact_claim.member_id = dim_member.member_id",
        ),
        Join(
            join_id=2,
            source_table="fact_member_month",
            target_table="dim_member",
            join_condition="fact_member_month.member_id = dim_member.member_id",
        ),
    ]
    graph = JoinGraph(joins)
    assert graph.is_connected({"fact_claim", "dim_member", "fact_member_month"})
    assert not graph.is_connected({"fact_member_month", "dim_provider"})


def test_validate_uses_metadata_tables(metadata: MetadataService):
    validate_sql(VALID_PMPM, metadata=metadata)


def test_rejects_unknown_table_with_metadata(metadata: MetadataService):
    with pytest.raises(SQLValidationError) as exc:
        validate_sql("SELECT * FROM secret_table", metadata=metadata)
    assert "Unknown table" in str(exc.value)


def test_rejects_invalid_join_path(metadata: MetadataService):
    with pytest.raises(SQLValidationError) as exc:
        validate_sql(
            """
            SELECT fmm.member_months, dp.provider_name
            FROM fact_member_month fmm
            JOIN dim_provider dp ON 1 = 1
            """,
            metadata=metadata,
        )
    assert exc.value.code == "INVALID_JOIN_PATH"


def test_rejects_metric_mismatch(metadata: MetadataService):
    intent = QuestionIntent(
        metric="PMPM",
        dimensions=["county"],
        filters={},
        raw_question="Show PMPM by county.",
    )
    with pytest.raises(SQLValidationError) as exc:
        validate_sql(
            """
            SELECT dm.county, COUNT(*) AS total
            FROM dim_member dm
            GROUP BY dm.county
            """,
            intent=intent,
            metadata=metadata,
        )
    assert exc.value.code == "METRIC_MISMATCH"


def test_rejects_dimension_mismatch(metadata: MetadataService):
    intent = QuestionIntent(
        metric="PMPM",
        dimensions=["age_group"],
        filters={},
        raw_question="Show PMPM by age group.",
    )
    with pytest.raises(SQLValidationError) as exc:
        validate_sql(
            """
            SELECT dm.county, SUM(fc.paid_amount) / NULLIF(SUM(fmm.member_months), 0) AS pmpm
            FROM fact_claim fc
            JOIN dim_member dm ON fc.member_id = dm.member_id
            JOIN fact_member_month fmm ON dm.member_id = fmm.member_id
            GROUP BY dm.county
            """,
            intent=intent,
            metadata=metadata,
        )
    assert exc.value.code == "DIMENSION_MISMATCH"
