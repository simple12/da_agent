from __future__ import annotations

import re
from typing import Any, Optional

import sqlparse
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import Keyword, Name

from app.models.question_intent import QuestionIntent
from app.schema import FORBIDDEN_KEYWORDS, METRIC_BASE_TABLES
from app.services.join_graph import JoinGraph
from app.services.metadata_service import MetadataService

# Fallback when metadata DB is unavailable (e.g. isolated unit tests).
_FALLBACK_APPROVED_TABLES: dict[str, set[str]] = {
    "fact_claim": {
        "claim_id",
        "member_id",
        "provider_id",
        "service_date",
        "paid_amount",
        "allowed_amount",
        "outstanding_amount",
        "claim_status",
    },
    "fact_member_month": {"member_id", "month_key", "member_months"},
    "dim_member": {"member_id", "county", "age_group", "lob"},
    "dim_provider": {"provider_id", "provider_name", "provider_group"},
}

_METRIC_SQL_MARKERS: dict[str, list[str]] = {
    "PMPM": ["paid_amount", "member_months"],
    "OUTSTANDING_CLAIMS": ["outstanding_amount"],
    "PENDING_CLAIMS": ["pending"],
    "CLAIMS_BY_STATUS": ["count"],
    "MEMBER_COUNT": ["member_id"],
}


class SQLValidationError(Exception):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message}


_SQL_KEYWORDS = frozenset(
    {
        "select",
        "from",
        "where",
        "join",
        "inner",
        "left",
        "right",
        "full",
        "cross",
        "on",
        "as",
        "and",
        "or",
        "not",
        "null",
        "true",
        "false",
        "sum",
        "count",
        "avg",
        "min",
        "max",
        "nullif",
        "coalesce",
        "case",
        "when",
        "then",
        "else",
        "end",
        "distinct",
        "group",
        "by",
        "order",
        "having",
        "limit",
        "offset",
        "asc",
        "desc",
        "in",
        "is",
        "like",
        "between",
        "exists",
        "all",
        "any",
        "union",
        "cast",
        "over",
        "partition",
        "paid",
        "pending",
        "approved",
    }
)


def _load_approved_tables(metadata: MetadataService | None) -> dict[str, set[str]]:
    if metadata is None:
        return _FALLBACK_APPROVED_TABLES
    try:
        tables = metadata.get_approved_tables()
        if tables:
            return tables
    except Exception:
        pass
    return _FALLBACK_APPROVED_TABLES


def _normalize_ident(name: str) -> str:
    return name.strip().strip('"').strip("'").lower()


def _extract_table_names(parsed, approved_tables: dict[str, set[str]]) -> set[str]:
    tables: set[str] = set()
    from_seen = False

    for token in parsed.tokens:
        if token.ttype is Keyword and token.value.upper() == "FROM":
            from_seen = True
            continue
        if from_seen:
            if token.ttype is Keyword and token.value.upper() in (
                "WHERE",
                "JOIN",
                "INNER",
                "LEFT",
                "RIGHT",
                "FULL",
                "CROSS",
                "GROUP",
                "ORDER",
                "HAVING",
                "LIMIT",
                "UNION",
            ):
                from_seen = False
            elif isinstance(token, IdentifierList):
                for ident in token.get_identifiers():
                    tables.add(_table_from_identifier(ident))
                from_seen = False
            elif isinstance(token, Identifier):
                tables.add(_table_from_identifier(token))
                from_seen = False
            elif token.ttype is Name:
                tables.add(_normalize_ident(token.value))
                from_seen = False

    sql = str(parsed)
    for match in re.finditer(
        r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        sql,
        re.IGNORECASE,
    ):
        tables.add(_normalize_ident(match.group(1)))

    return {t for t in tables if t in approved_tables or t}


def _table_from_identifier(ident: Identifier) -> str:
    name = ident.get_real_name() or ident.get_name() or str(ident)
    return _normalize_ident(name.split(".")[-1])


def _extract_alias_map(sql: str, approved_tables: dict[str, set[str]]) -> dict[str, str]:
    alias_map: dict[str, str] = {}

    for match in re.finditer(
        r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\b",
        sql,
        re.IGNORECASE,
    ):
        table = _normalize_ident(match.group(1))
        alias = _normalize_ident(match.group(2))
        if table in approved_tables and alias not in _SQL_KEYWORDS:
            alias_map[alias] = table

    for match in re.finditer(
        r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)\b",
        sql,
        re.IGNORECASE,
    ):
        table = _normalize_ident(match.group(1))
        if table in approved_tables:
            alias_map[table] = table

    for match in re.finditer(
        r"\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+ON\b",
        sql,
        re.IGNORECASE,
    ):
        table = _normalize_ident(match.group(1))
        alias = _normalize_ident(match.group(2))
        if table in approved_tables:
            alias_map[alias] = table

    return alias_map


def _resolve_table(
    prefix: str,
    alias_map: dict[str, str],
    tables: set[str],
    approved_tables: dict[str, set[str]],
) -> Optional[str]:
    prefix = _normalize_ident(prefix)
    if prefix in alias_map:
        return alias_map[prefix]
    if prefix in approved_tables and prefix in tables:
        return prefix
    return None


def _strip_literals(sql: str) -> str:
    sql = re.sub(r"'(?:''|[^'])*'", "''", sql)
    return re.sub(r'"(?:[^"]|"")*"', '""', sql)


def _validate_qualified_columns(
    sql: str,
    alias_map: dict[str, str],
    tables: set[str],
    approved_tables: dict[str, set[str]],
) -> None:
    for left, right in re.findall(
        r"([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b", sql
    ):
        left_norm = _normalize_ident(left)
        right_norm = _normalize_ident(right)
        table = _resolve_table(left_norm, alias_map, tables, approved_tables)
        if table is None:
            raise SQLValidationError(f"Unknown table or alias: {left}")
        if right_norm not in approved_tables[table]:
            raise SQLValidationError(f"Unknown column: {left}.{right}")


def _column_exists_in_tables(
    column: str, tables: set[str], approved_tables: dict[str, set[str]]
) -> bool:
    return any(column in approved_tables[table] for table in tables)


def _validate_unqualified_columns(
    sql: str, tables: set[str], approved_tables: dict[str, set[str]]
) -> None:
    stripped = _strip_literals(sql)

    select_match = re.search(
        r"\bSELECT\s+(?:DISTINCT\s+)?(.+?)\s+FROM\b",
        stripped,
        re.IGNORECASE | re.DOTALL,
    )
    if select_match:
        for part in select_match.group(1).split(","):
            part = part.strip()
            alias_match = re.search(r"\bAS\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*$", part, re.I)
            if alias_match:
                continue
            ident_match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)", part)
            if ident_match:
                col = _normalize_ident(ident_match.group(1))
                if col not in _SQL_KEYWORDS and not _column_exists_in_tables(
                    col, tables, approved_tables
                ):
                    raise SQLValidationError(f"Unknown column: {col}")

    for clause_pattern in (
        r"\bGROUP\s+BY\s+(.+?)(?:\bHAVING\b|\bORDER\b|\bLIMIT\b|$)",
        r"\bORDER\s+BY\s+(.+?)(?:\bLIMIT\b|$)",
    ):
        for match in re.finditer(clause_pattern, stripped, re.IGNORECASE | re.DOTALL):
            for part in match.group(1).split(","):
                part = part.strip()
                ident_match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)", part)
                if ident_match:
                    col = _normalize_ident(ident_match.group(1))
                    if col not in _SQL_KEYWORDS and not _column_exists_in_tables(
                        col, tables, approved_tables
                    ):
                        raise SQLValidationError(f"Unknown column: {col}")

    where_match = re.search(
        r"\bWHERE\b(.+?)(?:\bGROUP\b|\bORDER\b|\bHAVING\b|\bLIMIT\b|$)",
        stripped,
        re.IGNORECASE | re.DOTALL,
    )
    if where_match:
        for match in re.finditer(
            r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|<>|!=|<=|>=|<|>|IS|IN|LIKE|NOT\s+IN)\b",
            where_match.group(1),
            re.IGNORECASE,
        ):
            col = _normalize_ident(match.group(1))
            if col not in _SQL_KEYWORDS and not _column_exists_in_tables(
                col, tables, approved_tables
            ):
                raise SQLValidationError(f"Unknown column: {col}")


def _validate_join_path(
    tables: set[str], metadata: MetadataService | None
) -> None:
    if len(tables) <= 1 or metadata is None:
        return
    graph = JoinGraph(metadata.list_joins())
    if not graph.is_connected(tables):
        raise SQLValidationError(
            "Referenced tables are not connected via approved join paths.",
            code="INVALID_JOIN_PATH",
        )


def _validate_metric(sql: str, intent: QuestionIntent | None) -> None:
    if intent is None:
        return
    markers = _METRIC_SQL_MARKERS.get(intent.metric, [])
    lowered = sql.lower()
    missing = [marker for marker in markers if marker not in lowered]
    if missing:
        raise SQLValidationError(
            f"SQL does not match metric {intent.metric}; missing: {', '.join(missing)}",
            code="METRIC_MISMATCH",
        )


def _validate_dimensions(
    sql: str,
    intent: QuestionIntent | None,
    metadata: MetadataService | None,
) -> None:
    if intent is None or not intent.dimensions or metadata is None:
        return

    lowered = sql.lower()
    for dimension_name in intent.dimensions:
        dimension = metadata.get_dimension(dimension_name)
        if dimension is None:
            continue
        column = dimension.column_name.lower()
        if not re.search(rf"\b{re.escape(column)}\b", lowered):
            raise SQLValidationError(
                f"SQL missing requested dimension column: {dimension_name} ({column})",
                code="DIMENSION_MISMATCH",
            )


def _statement_type(parsed) -> str:
    return parsed.get_type() or "UNKNOWN"


def validate_sql(
    sql: str,
    intent: QuestionIntent | None = None,
    metadata: MetadataService | None = None,
) -> str:
    sql = sql.strip()
    if not sql:
        raise SQLValidationError("Empty SQL")

    approved_tables = _load_approved_tables(metadata)

    upper = sql.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            raise SQLValidationError(f"Forbidden keyword: {kw}")

    statements = sqlparse.parse(sql)
    if len(statements) != 1:
        raise SQLValidationError("Exactly one SQL statement is allowed")

    parsed = statements[0]
    stmt_type = _statement_type(parsed)
    if stmt_type != "SELECT" and "SELECT" not in upper.split()[0:3]:
        raise SQLValidationError(f"Only SELECT allowed, got: {stmt_type}")

    tables = _extract_table_names(parsed, approved_tables)
    if not tables:
        raise SQLValidationError("Could not determine tables in query")

    unknown_tables = tables - set(approved_tables.keys())
    if unknown_tables:
        raise SQLValidationError(f"Unknown table(s): {', '.join(sorted(unknown_tables))}")

    _validate_join_path(tables, metadata)

    alias_map = _extract_alias_map(sql, approved_tables)
    _validate_qualified_columns(sql, alias_map, tables, approved_tables)
    _validate_unqualified_columns(sql, tables, approved_tables)
    _validate_metric(sql, intent)
    _validate_dimensions(sql, intent, metadata)

    return sql
