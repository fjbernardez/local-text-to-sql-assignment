import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.exceptions.api_exceptions import LlmGenerationError

logger = logging.getLogger(__name__)

Transport = Callable[[str, dict[str, Any], float], dict[str, Any]]


class OllamaClient:
    def __init__(
        self,
        host: str,
        timeout_seconds: float,
        transport: Transport | None = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport or self._default_transport

    def generate(
        self,
        model: str,
        system: str,
        prompt: str,
        options: dict[str, Any],
    ) -> str:
        payload = {
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }

        try:
            response = self.transport(
                f"{self.host}/api/generate",
                payload,
                self.timeout_seconds,
            )
            raw_output = response["response"]
            if not isinstance(raw_output, str):
                raise TypeError("Ollama response field must be a string.")
            return raw_output
        except (KeyError, TypeError, ValueError) as exc:
            raise LlmGenerationError("Ollama returned an invalid response payload.") from exc
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            logger.warning("Ollama request failed error_type=%s", type(exc).__name__)
            raise LlmGenerationError("Ollama is unavailable or timed out.") from exc

    @staticmethod
    def _default_transport(
        url: str,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
