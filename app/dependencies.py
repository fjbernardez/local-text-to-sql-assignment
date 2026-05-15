from functools import lru_cache

from app.config.settings import get_settings
from app.llm.ollama_client import OllamaClient
from app.llm.ollama_natural_language_provider import OllamaNaturalLanguageProvider
from app.llm.ollama_sql_provider import OllamaSqlDecisionProvider
from app.services.ask_service import AskService
from app.services.sql_executor import SqlExecutor
from app.services.sql_validator import SqlValidator


@lru_cache
def build_ask_service() -> AskService:
    settings = get_settings()
    ollama_client = OllamaClient(
        host=settings.ollama_host,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    return AskService(
        sql_decision_provider=OllamaSqlDecisionProvider(client=ollama_client),
        natural_language_provider=OllamaNaturalLanguageProvider(client=ollama_client),
        validator=SqlValidator(),
        executor=SqlExecutor(),
    )
