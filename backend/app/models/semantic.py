from __future__ import annotations

from pydantic import BaseModel, Field


class Metric(BaseModel):
    metric_id: int
    metric_name: str
    metric_definition: str
    metric_formula: str
    aggregation_type: str
    business_owner: str = "analytics"


class Dimension(BaseModel):
    dimension_id: int
    dimension_name: str
    table_name: str
    column_name: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)


class SemanticTable(BaseModel):
    table_id: int
    table_name: str
    description: str = ""


class TableColumn(BaseModel):
    column_id: int
    table_name: str
    column_name: str
    description: str = ""


class Join(BaseModel):
    join_id: int
    source_table: str
    target_table: str
    join_condition: str
    join_type: str = "INNER"


class SampleQuery(BaseModel):
    query_id: int
    question_pattern: str
    sql_template: str
    metric_name: str | None = None
    description: str = ""
