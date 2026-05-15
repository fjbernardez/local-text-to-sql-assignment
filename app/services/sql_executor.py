import logging
import time
from typing import Any

import psycopg

from app.db.connection import connect
from app.exceptions.api_exceptions import SqlExecutionError

logger = logging.getLogger(__name__)


class SqlExecutor:
    def execute(self, sql: str, max_rows: int) -> list[dict[str, Any]]:
        started = time.perf_counter()
        try:
            with connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL statement_timeout = '5000ms'")
                    cursor.execute("SET LOCAL transaction_read_only = on")
                    cursor.execute(sql)
                    rows = list(cursor.fetchmany(max_rows))
        except psycopg.OperationalError as exc:
            raise SqlExecutionError("Database is unavailable.", status_code=503) from exc
        except psycopg.Error as exc:
            raise SqlExecutionError("Validated SQL could not be executed safely.") from exc

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "Query executed duration_ms=%s row_count=%s",
            round(duration_ms, 2),
            len(rows),
        )
        return rows
