import logging

from typing import Any

from app.exceptions.api_exceptions import LlmGenerationError, UnsafeSqlError
from app.llm.provider import NaturalLanguageProvider, SqlDecisionProvider
from app.prompts.sales_schema import SALES_SCHEMA_CONTEXT
from app.schemas.ask import AskResponse
from app.services.sql_executor import SqlExecutor
from app.services.sql_validator import SqlValidator

logger = logging.getLogger(__name__)


class AskService:
    def __init__(
        self,
        sql_decision_provider: SqlDecisionProvider,
        natural_language_provider: NaturalLanguageProvider,
        validator: SqlValidator,
        executor: SqlExecutor,
    ) -> None:
        self.sql_decision_provider = sql_decision_provider
        self.natural_language_provider = natural_language_provider
        self.validator = validator
        self.executor = executor

    def ask(
        self,
        question: str,
        max_rows: int,
        include_natural_answer: bool = True,
    ) -> AskResponse:
        logger.info("Ask request received")

        decision = self.sql_decision_provider.generate_decision(
            question=question,
            max_rows=max_rows,
            schema_context=SALES_SCHEMA_CONTEXT,
        )
        logger.info("LLM decision type=%s", decision.type)

        if decision.type in {"ambiguous", "unsupported"}:
            return AskResponse(
                type=decision.type,
                message=decision.message,
                sql=None,
                data=None,
                natural_message=None,
            )

        validation_result = self._validate_or_repair(question, max_rows, decision.sql)
        if isinstance(validation_result, AskResponse):
            return validation_result

        safe_sql = validation_result
        logger.info("SQL validation succeeded sql=%s", safe_sql)

        data = self.executor.execute(safe_sql, max_rows)
        natural_message = (
            self._generate_natural_message(question, safe_sql, data)
            if include_natural_answer
            else None
        )
        return AskResponse(
            type="query",
            message="Query executed successfully.",
            sql=safe_sql,
            data=data,
            natural_message=natural_message,
        )

    def _generate_natural_message(
        self,
        question: str,
        sql: str,
        data: list[dict[str, Any]],
    ) -> str | None:
        try:
            return self.natural_language_provider.generate_message(
                question=question,
                sql=sql,
                data=data,
            )
        except LlmGenerationError as exc:
            logger.warning(
                "Natural language generation failed; returning query data without natural_message error=%s",
                str(exc),
            )
            return None

    def _validate_or_repair(
        self,
        question: str,
        max_rows: int,
        sql: str | None,
    ) -> str | AskResponse:
        try:
            return self.validator.validate(sql or "", max_rows)
        except UnsafeSqlError as first_error:
            logger.warning(
                "SQL validation failed; requesting one repair attempt error=%s",
                str(first_error),
            )

            repair = self.sql_decision_provider.repair_decision(
                question=question,
                max_rows=max_rows,
                schema_context=SALES_SCHEMA_CONTEXT,
                invalid_sql=sql or "",
                validator_error=str(first_error),
            )
            logger.info("LLM repair decision type=%s", repair.type)

            if repair.type in {"ambiguous", "unsupported"}:
                return AskResponse(
                    type=repair.type,
                    message=repair.message,
                    sql=None,
                    data=None,
                    natural_message=None,
                )

            try:
                return self.validator.validate(repair.sql or "", max_rows)
            except UnsafeSqlError as repair_error:
                logger.warning(
                    "SQL repair validation failed error=%s",
                    str(repair_error),
                )
                raise repair_error from first_error
