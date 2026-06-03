from __future__ import annotations

import pytest

from app.models.errors import QuestionAnalysisError
from app.services.metadata_service import MetadataService
from app.services.question_analyzer import QuestionAnalyzer


@pytest.fixture
def analyzer() -> QuestionAnalyzer:
    return QuestionAnalyzer(MetadataService())


def test_pmpm_alameda(analyzer: QuestionAnalyzer):
    intent = analyzer.analyze("What is PMPM for Alameda County?")
    assert intent.metric == "PMPM"
    assert intent.filters["county"] == "Alameda"
    assert intent.dimensions == []


def test_pmpm_alameda_by_age(analyzer: QuestionAnalyzer):
    intent = analyzer.analyze(
        "What is PMPM for Alameda County and stratify by age group?"
    )
    assert intent.metric == "PMPM"
    assert intent.filters["county"] == "Alameda"
    assert intent.dimensions == ["age_group"]


def test_pmpm_by_county(analyzer: QuestionAnalyzer):
    intent = analyzer.analyze("Show PMPM by county.")
    assert intent.metric == "PMPM"
    assert intent.dimensions == ["county"]


def test_pmpm_by_county_and_lob(analyzer: QuestionAnalyzer):
    intent = analyzer.analyze("What is PMPM by county and LOB?")
    assert intent.metric == "PMPM"
    assert set(intent.dimensions) == {"county", "lob"}


def test_outstanding_by_provider(analyzer: QuestionAnalyzer):
    intent = analyzer.analyze("Outstanding claims by provider.")
    assert intent.metric == "OUTSTANDING_CLAIMS"
    assert intent.dimensions == ["provider_name"]


def test_pending_claims(analyzer: QuestionAnalyzer):
    intent = analyzer.analyze("How many claims are pending payment?")
    assert intent.metric == "PENDING_CLAIMS"


def test_ambiguous_by_group(analyzer: QuestionAnalyzer):
    with pytest.raises(QuestionAnalysisError) as exc:
        analyzer.analyze("Show PMPM by group.")
    assert exc.value.code == "AMBIGUOUS_DIMENSION"
    assert "provider_group" in exc.value.options


def test_unknown_metric(analyzer: QuestionAnalyzer):
    with pytest.raises(QuestionAnalysisError) as exc:
        analyzer.analyze("Show revenue by region.")
    assert exc.value.code == "UNKNOWN_METRIC"
