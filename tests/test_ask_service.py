import pytest

from app.exceptions.api_exceptions import LlmGenerationError, UnsafeSqlError
from app.schemas.llm import LlmDecision
from app.services.ask_service import AskService
from app.llm.provider import SqlDecisionProvider


class FakeGenerator:
    def __init__(self, decisions: list[LlmDecision] | None = None, error: Exception | None = None):
        self.decisions = decisions or []
        self.error = error
        self.generate_calls = 0
        self.repair_calls = 0

    def generate_decision(
        self,
        question: str,
        max_rows: int,
        schema_context: str,
    ) -> LlmDecision:
        self.generate_calls += 1
        if self.error:
            raise self.error
        return self.decisions.pop(0)

    def repair_decision(
        self,
        question: str,
        max_rows: int,
        schema_context: str,
        invalid_sql: str,
        validator_error: str,
    ) -> LlmDecision:
        self.repair_calls += 1
        return self.decisions.pop(0)


class FakeNaturalLanguageProvider:
    def __init__(self, message: str = "Coffee is the top product.", error: Exception | None = None):
        self.message = message
        self.error = error
        self.calls = 0
        self.question = None
        self.sql = None
        self.data = None

    def generate_message(
        self,
        question: str,
        sql: str,
        data: list[dict],
    ) -> str:
        self.calls += 1
        self.question = question
        self.sql = sql
        self.data = data
        if self.error:
            raise self.error
        return self.message


class FakeValidator:
    def __init__(self, results: list[str | Exception]):
        self.results = results
        self.calls = 0

    def validate(self, sql: str, max_rows: int) -> str:
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeExecutor:
    def __init__(self) -> None:
        self.calls = 0
        self.sql = None

    def execute(self, sql: str, max_rows: int) -> list[dict[str, int | str]]:
        self.calls += 1
        self.sql = sql
        return [{"product_name": "Coffee", "total_quantity": 213}]


def test_ambiguous_response_returns_without_executing_sql() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="ambiguous",
                sql=None,
                message="Please submit a new complete question.",
                confidence=0.8,
            )
        ]
    )
    validator = FakeValidator([])
    executor = FakeExecutor()
    natural_language = FakeNaturalLanguageProvider()

    response = AskService(generator, natural_language, validator, executor).ask("best customers", 50)

    assert response.type == "ambiguous"
    assert response.sql is None
    assert response.data is None
    assert response.natural_message is None
    assert validator.calls == 0
    assert executor.calls == 0
    assert natural_language.calls == 0


def test_no_clear_decision_returns_clarification_without_executing_sql() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="ambiguous",
                sql=None,
                message="Please clarify the metric. Do you mean by total revenue, quantity sold, number of tickets, or average ticket value?",
                confidence=None,
            )
        ]
    )
    validator = FakeValidator([])
    executor = FakeExecutor()
    natural_language = FakeNaturalLanguageProvider()

    response = AskService(generator, natural_language, validator, executor).ask("What is the best product?", 50)

    assert response.type == "ambiguous"
    assert "clarify the metric" in response.message
    assert response.sql is None
    assert response.data is None
    assert response.natural_message is None
    assert validator.calls == 0
    assert executor.calls == 0
    assert natural_language.calls == 0


def test_ask_service_accepts_fake_sql_decision_provider() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="ambiguous",
                sql=None,
                message="Please submit a new complete question.",
                confidence=0.8,
            )
        ]
    )

    assert isinstance(generator, SqlDecisionProvider)


def test_unsupported_response_returns_without_executing_sql() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="unsupported",
                sql=None,
                message="This cannot be answered from sales.",
                confidence=0.9,
            )
        ]
    )
    validator = FakeValidator([])
    executor = FakeExecutor()
    natural_language = FakeNaturalLanguageProvider()

    response = AskService(generator, natural_language, validator, executor).ask("Bitcoin prices", 50)

    assert response.type == "unsupported"
    assert response.natural_message is None
    assert validator.calls == 0
    assert executor.calls == 0
    assert natural_language.calls == 0


def test_valid_query_validates_and_executes() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="query",
                sql="SELECT product_name FROM sales",
                message="ok",
                confidence=0.9,
            )
        ]
    )
    validator = FakeValidator(["SELECT product_name FROM sales LIMIT 50"])
    executor = FakeExecutor()
    natural_language = FakeNaturalLanguageProvider("Coffee is the top product by quantity sold.")

    response = AskService(generator, natural_language, validator, executor).ask("products", 50)

    assert response.type == "query"
    assert response.sql == "SELECT product_name FROM sales LIMIT 50"
    assert response.data == [{"product_name": "Coffee", "total_quantity": 213}]
    assert response.natural_message == "Coffee is the top product by quantity sold."
    assert executor.calls == 1
    assert natural_language.calls == 1
    assert natural_language.sql == "SELECT product_name FROM sales LIMIT 50"


def test_valid_query_skips_natural_language_when_disabled() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="query",
                sql="SELECT product_name FROM sales",
                message="ok",
                confidence=0.9,
            )
        ]
    )
    validator = FakeValidator(["SELECT product_name FROM sales LIMIT 50"])
    executor = FakeExecutor()
    natural_language = FakeNaturalLanguageProvider()

    response = AskService(generator, natural_language, validator, executor).ask(
        "products",
        50,
        include_natural_answer=False,
    )

    assert response.type == "query"
    assert response.natural_message is None
    assert natural_language.calls == 0


def test_valid_query_still_returns_data_when_natural_language_generation_fails() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="query",
                sql="SELECT product_name FROM sales",
                message="ok",
                confidence=0.9,
            )
        ]
    )
    validator = FakeValidator(["SELECT product_name FROM sales LIMIT 50"])
    executor = FakeExecutor()
    natural_language = FakeNaturalLanguageProvider(
        error=LlmGenerationError("Ollama is unavailable.")
    )

    response = AskService(generator, natural_language, validator, executor).ask("products", 50)

    assert response.type == "query"
    assert response.sql == "SELECT product_name FROM sales LIMIT 50"
    assert response.data == [{"product_name": "Coffee", "total_quantity": 213}]
    assert response.natural_message is None
    assert executor.calls == 1
    assert natural_language.calls == 1


def test_invalid_generated_sql_triggers_exactly_one_repair_attempt() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="query",
                sql="DELETE FROM sales",
                message="ok",
                confidence=0.9,
            ),
            LlmDecision(
                type="query",
                sql="SELECT product_name FROM sales",
                message="repaired",
                confidence=0.9,
            ),
        ]
    )
    validator = FakeValidator(
        [
            UnsafeSqlError("Only SELECT queries are allowed."),
            "SELECT product_name FROM sales LIMIT 50",
        ]
    )
    executor = FakeExecutor()
    natural_language = FakeNaturalLanguageProvider()

    response = AskService(generator, natural_language, validator, executor).ask("products", 50)

    assert response.type == "query"
    assert generator.repair_calls == 1
    assert validator.calls == 2
    assert executor.calls == 1
    assert natural_language.calls == 1


def test_invalid_sql_after_repair_raises_safe_422_error() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="query",
                sql="DELETE FROM sales",
                message="ok",
                confidence=0.9,
            ),
            LlmDecision(
                type="query",
                sql="DROP TABLE sales",
                message="bad repair",
                confidence=0.9,
            ),
        ]
    )
    validator = FakeValidator(
        [
            UnsafeSqlError("Only SELECT queries are allowed."),
            UnsafeSqlError("Only SELECT queries are allowed."),
        ]
    )
    executor = FakeExecutor()

    with pytest.raises(UnsafeSqlError):
        AskService(generator, FakeNaturalLanguageProvider(), validator, executor).ask("products", 50)

    assert generator.repair_calls == 1
    assert executor.calls == 0


def test_repair_can_return_ambiguous_without_executing_sql() -> None:
    generator = FakeGenerator(
        [
            LlmDecision(
                type="query",
                sql="SELECT * FROM sales",
                message="ok",
                confidence=0.9,
            ),
            LlmDecision(
                type="ambiguous",
                sql=None,
                message="Please submit a new complete question clarifying the metric.",
                confidence=0.8,
            ),
        ]
    )
    validator = FakeValidator([UnsafeSqlError("Generated SQL is ambiguous.")])
    executor = FakeExecutor()
    natural_language = FakeNaturalLanguageProvider()

    response = AskService(generator, natural_language, validator, executor).ask("top products", 50)

    assert response.type == "ambiguous"
    assert response.sql is None
    assert response.data is None
    assert response.natural_message is None
    assert generator.repair_calls == 1
    assert executor.calls == 0
    assert natural_language.calls == 0


def test_ollama_error_maps_to_service_level_error() -> None:
    generator = FakeGenerator(error=LlmGenerationError("Ollama is unavailable."))
    service = AskService(
        generator,
        FakeNaturalLanguageProvider(),
        FakeValidator([]),
        FakeExecutor(),
    )

    with pytest.raises(LlmGenerationError):
        service.ask("products", 50)
