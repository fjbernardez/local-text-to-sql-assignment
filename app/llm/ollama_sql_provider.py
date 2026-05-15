from pydantic import ValidationError

from app.exceptions.api_exceptions import LlmGenerationError
from app.prompts.sql_generation_prompt import (
    SQL_GENERATION_SYSTEM_PROMPT,
    build_generation_input,
    build_repair_input,
)
from app.schemas.llm import LlmDecision
from app.config.settings import get_settings
from app.llm.ollama_client import OllamaClient, Transport
from app.llm.ollama_sql_response_parser import (
    parse_ollama_raw_output,
)


class OllamaSqlDecisionProvider:
    def __init__(
        self,
        client: OllamaClient | None = None,
        host: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        num_predict: int | None = None,
        transport: Transport | None = None,
    ) -> None:
        settings = get_settings()
        resolved_host = host or settings.ollama_host
        resolved_timeout = timeout_seconds or settings.ollama_timeout_seconds
        self.client = client or OllamaClient(
            host=resolved_host,
            timeout_seconds=resolved_timeout,
            transport=transport,
        )
        self.model = model or settings.ollama_model_sql
        self.temperature = (
            temperature if temperature is not None else settings.ollama_temperature_sql
        )
        self.top_p = top_p if top_p is not None else settings.ollama_top_p
        self.num_predict = num_predict or settings.ollama_num_predict_sql

    def generate_decision(
        self,
        question: str,
        max_rows: int,
        schema_context: str,
    ) -> LlmDecision:
        prompt_input = build_generation_input(
            schema_context=schema_context,
            question=question,
            max_rows=max_rows,
        )
        return self._request_decision(prompt_input)

    def repair_decision(
        self,
        question: str,
        max_rows: int,
        schema_context: str,
        invalid_sql: str,
        validator_error: str,
    ) -> LlmDecision:
        prompt_input = build_repair_input(
            schema_context=schema_context,
            question=question,
            max_rows=max_rows,
            invalid_sql=invalid_sql,
            validator_error=validator_error,
        )
        return self._request_decision(prompt_input)

    def _request_decision(self, prompt_input: str) -> LlmDecision:
        try:
            raw_output = self.client.generate(
                model=self.model,
                system=SQL_GENERATION_SYSTEM_PROMPT,
                prompt=prompt_input,
                options={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "num_predict": self.num_predict,
                },
            )
            return parse_ollama_raw_output(raw_output)
        except ValidationError as exc:
            raise LlmGenerationError("Ollama returned an invalid decision.") from exc
