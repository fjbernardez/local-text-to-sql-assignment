from typing import Any

from app.config.settings import get_settings
from app.exceptions.api_exceptions import LlmGenerationError
from app.llm.ollama_client import OllamaClient, Transport
from app.prompts.natural_response_prompt import (
    NATURAL_RESPONSE_SYSTEM_PROMPT,
    build_natural_response_input,
)


class OllamaNaturalLanguageProvider:
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
        self.model = model or settings.ollama_model_nl
        self.temperature = (
            temperature if temperature is not None else settings.ollama_temperature_nl
        )
        self.top_p = top_p if top_p is not None else settings.ollama_top_p
        self.num_predict = num_predict or settings.ollama_num_predict_nl

    def generate_message(
        self,
        question: str,
        sql: str,
        data: list[dict[str, Any]],
    ) -> str:
        prompt_input = build_natural_response_input(
            question=question,
            sql=sql,
            data=data,
        )
        raw_output = self.client.generate(
            model=self.model,
            system=NATURAL_RESPONSE_SYSTEM_PROMPT,
            prompt=prompt_input,
            options={
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_predict": self.num_predict,
            },
        )
        message = raw_output.strip()
        if not message:
            raise LlmGenerationError("Ollama returned an empty natural language response.")
        return message
