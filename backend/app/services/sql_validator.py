import re

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Parenthesis, Token
from sqlparse.tokens import Keyword, Name

from app.schema import APPROVED_TABLES, FORBIDDEN_KEYWORDS


class SQLValidationError(Exception):
    pass


def _normalize_ident(name: str) -> str:
    return name.strip().strip('"').strip("'").lower()


def _extract_table_names(parsed) -> set[str]:
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

        if token.ttype is Keyword and token.value.upper() in ("JOIN",):
            # next identifier is a table
            pass

    # Fallback: regex on full SQL for JOIN/FROM clauses
    sql = str(parsed)
    for match in re.finditer(
        r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        sql,
        re.IGNORECASE,
    ):
        tables.add(_normalize_ident(match.group(1)))

    return {t for t in tables if t}


def _table_from_identifier(ident: Identifier) -> str:
    name = ident.get_real_name() or ident.get_name() or str(ident)
    return _normalize_ident(name.split(".")[-1])


def _statement_type(parsed) -> str:
    return parsed.get_type() or "UNKNOWN"


def validate_sql(sql: str) -> str:
    sql = sql.strip()
    if not sql:
        raise SQLValidationError("Empty SQL")

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

    tables = _extract_table_names(parsed)
    if not tables:
        raise SQLValidationError("Could not determine tables in query")

    unknown_tables = tables - set(APPROVED_TABLES.keys())
    if unknown_tables:
        raise SQLValidationError(f"Unknown table(s): {', '.join(sorted(unknown_tables))}")

    return sql
