from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.metadata_service import MetadataService

router = APIRouter(tags=["metadata"])
_service = MetadataService()


class MetricResponse(BaseModel):
    metric: str
    formula: str
    definition: str
    aggregation_type: str
    business_owner: str


class DimensionResponse(BaseModel):
    dimension: str
    table: str
    column: str
    description: str
    aliases: list[str]


class JoinResponse(BaseModel):
    source: str
    target: str
    join_condition: str
    join_type: str


@router.get("/metrics")
def list_metrics() -> list[MetricResponse]:
    return [
        MetricResponse(
            metric=m.metric_name,
            formula=m.metric_formula,
            definition=m.metric_definition,
            aggregation_type=m.aggregation_type,
            business_owner=m.business_owner,
        )
        for m in _service.list_metrics()
    ]


@router.get("/metrics/{metric_name}", response_model=MetricResponse)
def get_metric(metric_name: str) -> MetricResponse:
    metric = _service.get_metric(metric_name)
    if metric is None:
        raise HTTPException(status_code=404, detail=f"Metric not found: {metric_name}")
    return MetricResponse(
        metric=metric.metric_name,
        formula=metric.metric_formula,
        definition=metric.metric_definition,
        aggregation_type=metric.aggregation_type,
        business_owner=metric.business_owner,
    )


@router.get("/dimensions")
def list_dimensions() -> list[DimensionResponse]:
    return [
        DimensionResponse(
            dimension=d.dimension_name,
            table=d.table_name,
            column=d.column_name,
            description=d.description,
            aliases=d.aliases,
        )
        for d in _service.list_dimensions()
    ]


@router.get("/dimensions/{dimension_name}", response_model=DimensionResponse)
def get_dimension(dimension_name: str) -> DimensionResponse:
    dimension = _service.get_dimension(dimension_name)
    if dimension is None:
        raise HTTPException(status_code=404, detail=f"Dimension not found: {dimension_name}")
    return DimensionResponse(
        dimension=dimension.dimension_name,
        table=dimension.table_name,
        column=dimension.column_name,
        description=dimension.description,
        aliases=dimension.aliases,
    )


@router.get("/joins", response_model=list[JoinResponse])
def list_joins() -> list[JoinResponse]:
    return [
        JoinResponse(
            source=j.source_table,
            target=j.target_table,
            join_condition=j.join_condition,
            join_type=j.join_type,
        )
        for j in _service.list_joins()
    ]


@router.get("/tables")
def list_tables() -> list[dict]:
    return _service.tables_with_columns()
