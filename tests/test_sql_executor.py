from app.services.sql_executor import SqlExecutor


class FakeCursor:
    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql: str) -> None:
        self.executed_sql.append(sql)

    def fetchmany(self, max_rows: int) -> list[dict[str, int]]:
        return [{"ticket_count": 1}]


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self) -> FakeCursor:
        return self.fake_cursor


def test_sql_executor_sets_defensive_session_options(monkeypatch) -> None:
    cursor = FakeCursor()
    monkeypatch.setattr(
        "app.services.sql_executor.connect",
        lambda: FakeConnection(cursor),
    )

    rows = SqlExecutor().execute("SELECT COUNT(*) AS ticket_count FROM sales LIMIT 1", max_rows=1)

    assert rows == [{"ticket_count": 1}]
    assert cursor.executed_sql == [
        "SET LOCAL statement_timeout = '5000ms'",
        "SET LOCAL transaction_read_only = on",
        "SELECT COUNT(*) AS ticket_count FROM sales LIMIT 1",
    ]
