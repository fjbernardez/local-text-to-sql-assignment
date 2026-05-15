class LlmGenerationError(Exception):
    """Raised when the language model cannot return a usable decision."""


class UnsafeSqlError(Exception):
    """Raised when generated SQL cannot be validated as safe read-only SQL."""


class SqlExecutionError(Exception):
    """Raised when validated SQL cannot be executed safely."""

    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code
