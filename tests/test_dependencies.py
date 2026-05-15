from app.dependencies import build_ask_service
from app.llm.ollama_natural_language_provider import OllamaNaturalLanguageProvider
from app.llm.ollama_sql_provider import OllamaSqlDecisionProvider
from app.services.ask_service import AskService
from app.services.sql_executor import SqlExecutor
from app.services.sql_validator import SqlValidator


def test_build_ask_service_wires_production_dependencies(monkeypatch) -> None:
    build_ask_service.cache_clear()

    class FakeOllamaSqlDecisionProvider:
        def __init__(self, *args, **kwargs):
            pass

    class FakeOllamaNaturalLanguageProvider:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(
        "app.dependencies.OllamaSqlDecisionProvider",
        FakeOllamaSqlDecisionProvider,
    )
    monkeypatch.setattr(
        "app.dependencies.OllamaNaturalLanguageProvider",
        FakeOllamaNaturalLanguageProvider,
    )

    service = build_ask_service()

    assert isinstance(service, AskService)
    assert isinstance(service.sql_decision_provider, FakeOllamaSqlDecisionProvider)
    assert isinstance(
        service.natural_language_provider,
        FakeOllamaNaturalLanguageProvider,
    )
    assert isinstance(service.validator, SqlValidator)
    assert isinstance(service.executor, SqlExecutor)

    build_ask_service.cache_clear()


def test_build_ask_service_is_cached(monkeypatch) -> None:
    build_ask_service.cache_clear()

    class FakeOllamaSqlDecisionProvider:
        def __init__(self, *args, **kwargs):
            pass

    class FakeOllamaNaturalLanguageProvider:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(
        "app.dependencies.OllamaSqlDecisionProvider",
        FakeOllamaSqlDecisionProvider,
    )
    monkeypatch.setattr(
        "app.dependencies.OllamaNaturalLanguageProvider",
        FakeOllamaNaturalLanguageProvider,
    )

    first = build_ask_service()
    second = build_ask_service()

    assert first is second

    build_ask_service.cache_clear()


def test_dependency_module_owns_ollama_provider_import() -> None:
    assert OllamaSqlDecisionProvider is not None
    assert OllamaNaturalLanguageProvider is not None
