import json
from decimal import Decimal
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row

from app.config import settings


def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def execute_query(sql: str) -> list[dict]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [{k: _json_safe(v) for k, v in row.items()} for row in rows]
