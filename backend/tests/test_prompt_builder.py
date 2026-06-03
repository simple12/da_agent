from __future__ import annotations

import pytest

from app.models.question_intent import QuestionIntent
from app.services.metadata_service import MetadataService
from app.services.prompt_builder import PromptBuilder
from app.services.sql_generator import _mock_sql_from_metadata


@pytest.fixture
def prompt_builder() -> PromptBuilder:
    return PromptBuilder(MetadataService())


def test_prompt_includes_metric_not_full_catalog(prompt_builder: PromptBuilder):
    intent = QuestionIntent(
        metric="PMPM",
        dimensions=["county"],
        filters={},
        raw_question="Show PMPM by county.",
    )
    prompt = prompt_builder.build(intent)
    assert "Metric: PMPM" in prompt
    assert "SUM(paid_amount)" in prompt
    assert "dim_provider" not in prompt
    assert "fact_claim" in prompt
    assert "dim_member" in prompt


def test_prompt_includes_filters(prompt_builder: PromptBuilder):
    intent = QuestionIntent(
        metric="PMPM",
        dimensions=["age_group"],
        filters={"county": "Alameda"},
        raw_question="What is PMPM for Alameda County by age group?",
    )
    prompt = prompt_builder.build(intent)
    assert "Filters:" in prompt
    assert "Alameda" in prompt
    assert "age_group" in prompt


def test_mock_sql_from_metadata_pmpm_county():
    metadata = MetadataService()
    sql = _mock_sql_from_metadata("Show PMPM by county.", metadata)
    assert sql is not None
    assert "GROUP BY" in sql.upper()
    assert "county" in sql.lower()


def test_mock_sql_alameda_age_beats_alameda_only():
    metadata = MetadataService()
    sql = _mock_sql_from_metadata(
        "What is PMPM for Alameda County and stratify by age group?",
        metadata,
    )
    assert sql is not None
    assert "age_group" in sql.lower()
    assert "Alameda" in sql
