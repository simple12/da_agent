from __future__ import annotations

import pytest

from app.repositories.semantic_repo import SemanticRepository
from app.services.metadata_service import MetadataService


@pytest.fixture
def metadata_service() -> MetadataService:
    return MetadataService(SemanticRepository())


def test_list_metrics(metadata_service: MetadataService):
    metrics = metadata_service.list_metrics()
    names = {m.metric_name for m in metrics}
    assert "PMPM" in names
    assert "OUTSTANDING_CLAIMS" in names


def test_get_metric_pmpm(metadata_service: MetadataService):
    metric = metadata_service.get_metric("PMPM")
    assert metric is not None
    assert "paid_amount" in metric.metric_formula
    assert "member_months" in metric.metric_formula


def test_get_dimension_county(metadata_service: MetadataService):
    dimension = metadata_service.get_dimension("county")
    assert dimension is not None
    assert dimension.table_name == "dim_member"
    assert dimension.column_name == "county"


def test_list_joins(metadata_service: MetadataService):
    joins = metadata_service.list_joins()
    assert len(joins) >= 3
    pairs = {(j.source_table, j.target_table) for j in joins}
    assert ("fact_claim", "dim_member") in pairs


def test_get_approved_tables(metadata_service: MetadataService):
    tables = metadata_service.get_approved_tables()
    assert set(tables["fact_claim"]) >= {"paid_amount", "claim_status", "member_id"}


def test_list_sample_queries_for_metric(metadata_service: MetadataService):
    samples = metadata_service.list_sample_queries("PMPM")
    assert len(samples) >= 4
