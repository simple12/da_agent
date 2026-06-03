from __future__ import annotations

from app.models.question_intent import QuestionIntent
from app.models.semantic import Dimension, Join
from app.schema import METRIC_BASE_TABLES, SQL_DIALECT_RULES
from app.services.metadata_service import MetadataService


class PromptBuilder:
    def __init__(self, metadata: MetadataService | None = None) -> None:
        self._metadata = metadata or MetadataService()

    def build(self, intent: QuestionIntent) -> str:
        metric = self._metadata.get_metric(intent.metric)
        if metric is None:
            raise ValueError(f"Unknown metric: {intent.metric}")

        dimensions = [
            dim
            for name in intent.dimensions
            if (dim := self._metadata.get_dimension(name)) is not None
        ]

        required_tables = self._required_tables(intent.metric, dimensions)
        table_blocks = self._format_tables(required_tables)
        join_lines = self._relevant_joins(required_tables)
        examples = self._format_examples(intent.metric, intent.dimensions)
        filter_lines = self._format_filters(intent, dimensions)
        dimension_lines = self._format_dimensions(dimensions)

        parts = [
            "You are a healthcare SQL analyst.",
            "",
            f"Metric: {metric.metric_name}",
            f"Definition: {metric.metric_definition}",
            f"Formula: {metric.metric_formula}",
            "",
        ]

        if dimension_lines:
            parts.extend(["Dimensions:", *dimension_lines, ""])

        if filter_lines:
            parts.extend(["Filters:", *filter_lines, ""])

        parts.extend(
            [
                "Tables and columns (use ONLY these):",
                *table_blocks,
                "",
                "Relationships:",
                *join_lines,
                "",
            ]
        )

        if examples:
            parts.extend(["Examples:", *examples, ""])

        parts.extend(["Rules:", SQL_DIALECT_RULES.strip()])

        return "\n".join(parts)

    def _required_tables(self, metric_name: str, dimensions: list[Dimension]) -> set[str]:
        tables = set(METRIC_BASE_TABLES.get(metric_name, set()))
        for dim in dimensions:
            tables.add(dim.table_name)
        return tables

    def _format_tables(self, table_names: set[str]) -> list[str]:
        lines: list[str] = []
        for table in self._metadata.tables_with_columns():
            if table["table_name"] not in table_names:
                continue
            cols = ", ".join(col["column_name"] for col in table["columns"])
            lines.append(f"{table['table_name']} ({cols})")
            for col in table["columns"]:
                if col["description"]:
                    lines.append(f"- {table['table_name']}.{col['column_name']}: {col['description']}")
        return lines

    def _relevant_joins(self, table_names: set[str]) -> list[str]:
        joins: list[Join] = self._metadata.list_joins()
        lines: list[str] = []
        for join in joins:
            if join.source_table in table_names and join.target_table in table_names:
                lines.append(join.join_condition)
        return lines or ["(single-table query)"]

    def _format_dimensions(self, dimensions: list[Dimension]) -> list[str]:
        return [
            f"- {dim.dimension_name}: {dim.table_name}.{dim.column_name} — {dim.description}".rstrip(
                " — "
            )
            for dim in dimensions
        ]

    def _format_filters(
        self, intent: QuestionIntent, dimensions: list[Dimension]
    ) -> list[str]:
        if not intent.filters:
            return []
        dim_by_name = {dim.dimension_name: dim for dim in dimensions}
        lines: list[str] = []
        for key, value in intent.filters.items():
            if key in dim_by_name:
                dim = dim_by_name[key]
                lines.append(f"- {dim.table_name}.{dim.column_name} = '{value}'")
            elif key == "county":
                lines.append(f"- dim_member.county = '{value}'")
            elif key == "claim_status":
                lines.append(f"- fact_claim.claim_status = '{value}'")
            else:
                lines.append(f"- {key} = '{value}'")
        return lines

    def _format_examples(self, metric_name: str, dimension_names: list[str]) -> list[str]:
        samples = self._metadata.list_sample_queries(metric_name)
        if not samples:
            return []

        dim_set = set(dimension_names)
        ranked: list[tuple[int, str]] = []
        for sample in samples:
            score = 0
            pattern = sample.question_pattern.lower()
            if "by" in pattern and dim_set:
                for dim in dim_set:
                    if dim.replace("_", " ") in pattern or dim in pattern:
                        score += 2
            ranked.append((score, sample.description or sample.question_pattern))

        ranked.sort(key=lambda item: item[0], reverse=True)
        chosen = samples[:2]
        if ranked and ranked[0][0] > 0:
            best_desc = ranked[0][1]
            chosen = [s for s in samples if (s.description or s.question_pattern) == best_desc][:1]
            if len(chosen) < 2:
                for sample in samples:
                    if sample not in chosen:
                        chosen.append(sample)
                    if len(chosen) == 2:
                        break

        lines: list[str] = []
        for sample in chosen[:2]:
            label = sample.description or "Example"
            lines.append(f"{label}:")
            lines.append(sample.sql_template)
            lines.append("")
        return lines
