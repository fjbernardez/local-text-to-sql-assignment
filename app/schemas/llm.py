from typing import Literal

from pydantic import BaseModel


class LlmDecision(BaseModel):
    type: Literal["query", "ambiguous", "unsupported"]
    sql: str | None
    message: str
    confidence: float | None = None
