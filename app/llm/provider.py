from typing import Any, Protocol, runtime_checkable

from app.schemas.llm import LlmDecision


@runtime_checkable
class SqlDecisionProvider(Protocol):
    def generate_decision(
        self,
        question: str,
        max_rows: int,
        schema_context: str,
    ) -> LlmDecision:
        """Return a structured decision for a natural language question."""

    def repair_decision(
        self,
        question: str,
        max_rows: int,
        schema_context: str,
        invalid_sql: str,
        validator_error: str,
    ) -> LlmDecision:
        """Return one semantic correction attempt after validator rejection."""


@runtime_checkable
class NaturalLanguageProvider(Protocol):
    def generate_message(
        self,
        question: str,
        sql: str,
        data: list[dict[str, Any]],
    ) -> str:
        """Return a concise natural-language message for executed query results."""
