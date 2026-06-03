from __future__ import annotations

from typing import Optional

import psycopg
from psycopg.rows import dict_row

from app.config import settings
from app.models.semantic import (
    Dimension,
    Join,
    Metric,
    SampleQuery,
    SemanticTable,
    TableColumn,
)


class SemanticRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or settings.database_url

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def list_metrics(self) -> list[Metric]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT metric_id, metric_name, metric_definition, metric_formula,
                           aggregation_type, business_owner
                    FROM semantic.metrics
                    ORDER BY metric_name
                    """
                )
                return [Metric.model_validate(row) for row in cur.fetchall()]

    def get_metric(self, metric_name: str) -> Optional[Metric]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT metric_id, metric_name, metric_definition, metric_formula,
                           aggregation_type, business_owner
                    FROM semantic.metrics
                    WHERE UPPER(metric_name) = UPPER(%s)
                    """,
                    (metric_name,),
                )
                row = cur.fetchone()
                return Metric.model_validate(row) if row else None

    def list_dimensions(self) -> list[Dimension]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT dimension_id, dimension_name, table_name, column_name,
                           description, aliases
                    FROM semantic.dimensions
                    ORDER BY dimension_name
                    """
                )
                return [Dimension.model_validate(row) for row in cur.fetchall()]

    def get_dimension(self, dimension_name: str) -> Optional[Dimension]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT dimension_id, dimension_name, table_name, column_name,
                           description, aliases
                    FROM semantic.dimensions
                    WHERE LOWER(dimension_name) = LOWER(%s)
                    """,
                    (dimension_name,),
                )
                row = cur.fetchone()
                return Dimension.model_validate(row) if row else None

    def list_joins(self) -> list[Join]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT join_id, source_table, target_table, join_condition, join_type
                    FROM semantic.joins
                    ORDER BY source_table, target_table
                    """
                )
                return [Join.model_validate(row) for row in cur.fetchall()]

    def list_tables(self) -> list[SemanticTable]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_id, table_name, description
                    FROM semantic.tables
                    ORDER BY table_name
                    """
                )
                return [SemanticTable.model_validate(row) for row in cur.fetchall()]

    def list_table_columns(self, table_name: str | None = None) -> list[TableColumn]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if table_name:
                    cur.execute(
                        """
                        SELECT column_id, table_name, column_name, description
                        FROM semantic.table_columns
                        WHERE table_name = %s
                        ORDER BY column_name
                        """,
                        (table_name,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT column_id, table_name, column_name, description
                        FROM semantic.table_columns
                        ORDER BY table_name, column_name
                        """
                    )
                return [TableColumn.model_validate(row) for row in cur.fetchall()]

    def get_approved_tables(self) -> dict[str, set[str]]:
        columns = self.list_table_columns()
        tables: dict[str, set[str]] = {}
        for col in columns:
            tables.setdefault(col.table_name, set()).add(col.column_name)
        return tables

    def list_sample_queries(self, metric_name: str | None = None) -> list[SampleQuery]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if metric_name:
                    cur.execute(
                        """
                        SELECT query_id, question_pattern, sql_template, metric_name, description
                        FROM semantic.sample_queries
                        WHERE metric_name IS NOT NULL
                          AND UPPER(metric_name) = UPPER(%s)
                        ORDER BY query_id
                        """,
                        (metric_name,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT query_id, question_pattern, sql_template, metric_name, description
                        FROM semantic.sample_queries
                        ORDER BY query_id
                        """
                    )
                return [SampleQuery.model_validate(row) for row in cur.fetchall()]
