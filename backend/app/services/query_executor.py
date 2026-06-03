from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from trino.dbapi import connect as trino_connect

from app.config import settings


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _execute_postgres(sql: str) -> list[dict]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [{k: _json_safe(v) for k, v in row.items()} for row in rows]


def _execute_trino(sql: str) -> list[dict]:
    conn = trino_connect(
        host=settings.trino_host,
        port=settings.trino_port,
        user=settings.trino_user,
        catalog=settings.trino_catalog,
        schema=settings.trino_schema,
    )
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description or []]
        rows = cur.fetchall()
        return [
            {col: _json_safe(val) for col, val in zip(columns, row)} for row in rows
        ]
    finally:
        conn.close()


def execute_query(sql: str) -> list[dict]:
    engine = settings.query_engine.lower()
    if engine == "postgres":
        return _execute_postgres(sql)
    if engine == "trino":
        return _execute_trino(sql)
    raise ValueError(f"Unsupported query engine: {settings.query_engine}")
