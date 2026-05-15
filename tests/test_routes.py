import psycopg
from fastapi.testclient import TestClient

from app.api.v1.ask_router import get_ask_service
from app.exceptions.api_exceptions import (
    LlmGenerationError,
    SqlExecutionError,
    UnsafeSqlError,
)
from app.main import app
from app.schemas.ask import AskResponse


client = TestClient(app)


class FakeAskService:
    def __init__(self, response: AskResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error

    def ask(self, question: str, max_rows: int) -> AskResponse:
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql: str) -> None:
        self.sql = sql

    def fetchone(self) -> dict[str, int]:
        return {"ok": 1}


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self) -> FakeCursor:
        return FakeCursor()


def override_service(service: FakeAskService) -> None:
    app.dependency_overrides[get_ask_service] = lambda: service


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_public_openapi_paths_are_limited_to_supported_endpoints() -> None:
    assert set(app.openapi()["paths"]) == {"/health", "/db-health", "/ask"}


def test_health_route() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_health_route(monkeypatch) -> None:
    monkeypatch.setattr("app.main.connect", lambda: FakeConnection())

    response = client.get("/db-health")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


def test_db_health_route_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    def raise_operational_error():
        raise psycopg.OperationalError("unavailable")

    monkeypatch.setattr("app.main.connect", raise_operational_error)

    response = client.get("/db-health")

    assert response.status_code == 503
    assert "Database connectivity check failed" in response.json()["detail"]


def test_ask_route_uses_service_dependency() -> None:
    override_service(
        FakeAskService(
            AskResponse(
                type="ambiguous",
                message="Please submit a new complete question.",
                sql=None,
                data=None,
            )
        )
    )

    response = client.post("/ask", json={"question": "best customers", "max_rows": 50})

    assert response.status_code == 200
    assert response.json()["type"] == "ambiguous"


def test_removed_demo_routes_return_404() -> None:
    assert client.get("/artists/count").status_code == 404
    assert client.get("/artists/top-by-albums").status_code == 404


def test_unsafe_sql_exception_handler_is_registered() -> None:
    override_service(FakeAskService(error=UnsafeSqlError("unsafe")))

    response = client.post("/ask", json={"question": "products", "max_rows": 50})

    assert response.status_code == 422
    assert response.json() == {"detail": "unsafe"}


def test_llm_exception_handler_is_registered() -> None:
    override_service(FakeAskService(error=LlmGenerationError("Ollama unavailable")))

    response = client.post("/ask", json={"question": "products", "max_rows": 50})

    assert response.status_code == 503
    assert response.json() == {"detail": "Ollama unavailable"}


def test_sql_execution_exception_handler_is_registered() -> None:
    override_service(FakeAskService(error=SqlExecutionError("Database unavailable", 503)))

    response = client.post("/ask", json={"question": "products", "max_rows": 50})

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
