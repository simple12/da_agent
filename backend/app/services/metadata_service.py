from __future__ import annotations

from app.models.semantic import Dimension, Join, Metric, SampleQuery, SemanticTable, TableColumn
from app.repositories.semantic_repo import SemanticRepository


class MetadataService:
    def __init__(self, repo: SemanticRepository | None = None) -> None:
        self._repo = repo or SemanticRepository()

    def list_metrics(self) -> list[Metric]:
        return self._repo.list_metrics()

    def get_metric(self, metric_name: str) -> Metric | None:
        return self._repo.get_metric(metric_name)

    def list_dimensions(self) -> list[Dimension]:
        return self._repo.list_dimensions()

    def get_dimension(self, dimension_name: str) -> Dimension | None:
        return self._repo.get_dimension(dimension_name)

    def list_joins(self) -> list[Join]:
        return self._repo.list_joins()

    def list_tables(self) -> list[SemanticTable]:
        return self._repo.list_tables()

    def list_table_columns(self, table_name: str | None = None) -> list[TableColumn]:
        return self._repo.list_table_columns(table_name)

    def get_approved_tables(self) -> dict[str, set[str]]:
        return self._repo.get_approved_tables()

    def list_sample_queries(self, metric_name: str | None = None) -> list[SampleQuery]:
        return self._repo.list_sample_queries(metric_name)

    def tables_with_columns(self) -> list[dict]:
        tables = self.list_tables()
        columns = self.list_table_columns()
        by_table: dict[str, list[TableColumn]] = {}
        for col in columns:
            by_table.setdefault(col.table_name, []).append(col)
        return [
            {
                "table_name": table.table_name,
                "description": table.description,
                "columns": [
                    {
                        "column_name": col.column_name,
                        "description": col.description,
                    }
                    for col in sorted(by_table.get(table.table_name, []), key=lambda c: c.column_name)
                ],
            }
            for table in tables
        ]

    def join_lines(self) -> list[str]:
        return [join.join_condition for join in self.list_joins()]

    def metric_count(self) -> int:
        return len(self.list_metrics())
