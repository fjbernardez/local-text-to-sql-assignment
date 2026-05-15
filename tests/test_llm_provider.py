import pytest

from app.exceptions.api_exceptions import LlmGenerationError
from app.llm.ollama_natural_language_provider import OllamaNaturalLanguageProvider
from app.llm.ollama_sql_response_parser import (
    CLARIFICATION_MESSAGE,
    UNSUPPORTED_MESSAGE,
)
from app.llm.ollama_sql_provider import OllamaSqlDecisionProvider
from app.llm.provider import NaturalLanguageProvider, SqlDecisionProvider
from app.schemas.llm import LlmDecision


class FakeTransport:
    def __init__(self, response: dict):
        self.response = response
        self.calls: list[tuple[str, dict, float]] = []

    def __call__(self, url: str, payload: dict, timeout: float) -> dict:
        self.calls.append((url, payload, timeout))
        return self.response


class FakeProvider:
    def generate_decision(
        self,
        question: str,
        max_rows: int,
        schema_context: str,
    ) -> LlmDecision:
        return LlmDecision(type="unsupported", sql=None, message="no", confidence=0.1)

    def repair_decision(
        self,
        question: str,
        max_rows: int,
        schema_context: str,
        invalid_sql: str,
        validator_error: str,
    ) -> LlmDecision:
        return LlmDecision(type="unsupported", sql=None, message="no", confidence=0.1)


class FakeNaturalLanguageProvider:
    def generate_message(
        self,
        question: str,
        sql: str,
        data: list[dict],
    ) -> str:
        return "Coffee is the top product."


def test_sql_decision_provider_protocol_accepts_matching_provider() -> None:
    assert isinstance(FakeProvider(), SqlDecisionProvider)


def test_natural_language_provider_protocol_accepts_matching_provider() -> None:
    assert isinstance(FakeNaturalLanguageProvider(), NaturalLanguageProvider)


def test_ollama_provider_maps_sql_response_to_query_decision() -> None:
    transport = FakeTransport(
        {"response": "SELECT product_name FROM sales ORDER BY product_name LIMIT 5"}
    )
    provider = OllamaSqlDecisionProvider(
        host="http://ollama:11434",
        model="qwen2.5-coder:3b",
        timeout_seconds=12,
        transport=transport,
    )

    decision = provider.generate_decision(
        question="products",
        max_rows=5,
        schema_context="sales table schema",
    )

    assert decision.type == "query"
    assert decision.sql == "SELECT product_name FROM sales ORDER BY product_name LIMIT 5"
    assert transport.calls[0][0] == "http://ollama:11434/api/generate"
    assert transport.calls[0][1]["model"] == "qwen2.5-coder:3b"
    assert transport.calls[0][1]["stream"] is False
    assert transport.calls[0][1]["options"]["temperature"] == 0
    assert "sales table schema" in transport.calls[0][1]["prompt"]


def test_ollama_provider_maps_fenced_sql_response_to_query_decision() -> None:
    provider = OllamaSqlDecisionProvider(
        transport=FakeTransport({"response": "```sql\nSELECT * FROM sales LIMIT 5;\n```"}),
    )

    decision = provider.generate_decision(
        question="products",
        max_rows=5,
        schema_context="sales table schema",
    )

    assert decision.type == "query"
    assert decision.sql == "SELECT * FROM sales LIMIT 5;"


def test_ollama_provider_maps_ambiguous_to_ambiguous_decision() -> None:
    provider = OllamaSqlDecisionProvider(
        transport=FakeTransport({"response": "AMBIGUOUS"}),
    )

    decision = provider.generate_decision(
        question="What is the best product?",
        max_rows=50,
        schema_context="sales table schema",
    )

    assert decision.type == "ambiguous"
    assert decision.sql is None
    assert decision.message == CLARIFICATION_MESSAGE


def test_ollama_provider_maps_ambiguous_with_period_to_ambiguous_decision() -> None:
    provider = OllamaSqlDecisionProvider(
        transport=FakeTransport({"response": "AMBIGUOUS."}),
    )

    decision = provider.generate_decision(
        question="What is the best product?",
        max_rows=50,
        schema_context="sales table schema",
    )

    assert decision.type == "ambiguous"
    assert decision.sql is None
    assert decision.message == CLARIFICATION_MESSAGE


def test_ollama_provider_maps_unsupported_to_unsupported_decision() -> None:
    provider = OllamaSqlDecisionProvider(
        transport=FakeTransport({"response": "UNSUPPORTED"}),
    )

    decision = provider.generate_decision(
        question="What is the weather tomorrow?",
        max_rows=50,
        schema_context="sales table schema",
    )

    assert decision.type == "unsupported"
    assert decision.sql is None
    assert decision.message == UNSUPPORTED_MESSAGE


def test_ollama_provider_maps_unsupported_with_period_to_unsupported_decision() -> None:
    provider = OllamaSqlDecisionProvider(
        transport=FakeTransport({"response": "UNSUPPORTED."}),
    )

    decision = provider.generate_decision(
        question="What is the weather tomorrow?",
        max_rows=50,
        schema_context="sales table schema",
    )

    assert decision.type == "unsupported"
    assert decision.sql is None
    assert decision.message == UNSUPPORTED_MESSAGE


@pytest.mark.parametrize(
    "response",
    [
        {"response": ""},
        {"response": "NO_CLEAR"},
        {"response": "Here is the SQL: SELECT * FROM sales"},
        {"response": '{"sql": "SELECT * FROM sales"}'},
        {},
    ],
)
def test_ollama_provider_rejects_invalid_model_response(response: dict) -> None:
    provider = OllamaSqlDecisionProvider(transport=FakeTransport(response))

    with pytest.raises(LlmGenerationError):
        provider.generate_decision(
            question="products",
            max_rows=50,
            schema_context="sales table schema",
        )


def test_ollama_natural_language_provider_returns_message() -> None:
    transport = FakeTransport({"response": "Coffee is the top product by quantity sold."})
    provider = OllamaNaturalLanguageProvider(
        host="http://ollama:11434",
        model="llama3.2:3b",
        timeout_seconds=12,
        transport=transport,
    )

    message = provider.generate_message(
        question="top product",
        sql="SELECT product_name FROM sales LIMIT 1",
        data=[{"product_name": "Coffee", "total_quantity": 213}],
    )

    assert message == "Coffee is the top product by quantity sold."
    assert transport.calls[0][0] == "http://ollama:11434/api/generate"
    assert transport.calls[0][1]["model"] == "llama3.2:3b"
    assert transport.calls[0][1]["stream"] is False
    assert transport.calls[0][1]["options"]["temperature"] == 0.2
    assert "top product" in transport.calls[0][1]["prompt"]


def test_ollama_natural_language_provider_rejects_empty_response() -> None:
    provider = OllamaNaturalLanguageProvider(
        transport=FakeTransport({"response": ""}),
    )

    with pytest.raises(LlmGenerationError):
        provider.generate_message(
            question="top product",
            sql="SELECT product_name FROM sales LIMIT 1",
            data=[],
        )
