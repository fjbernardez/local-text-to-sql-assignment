from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions.api_exceptions import (
    LlmGenerationError,
    SqlExecutionError,
    UnsafeSqlError,
)


def handle_llm_generation_error(
    request: Request,
    exc: LlmGenerationError,
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def handle_unsafe_sql_error(request: Request, exc: UnsafeSqlError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def handle_sql_execution_error(
    request: Request,
    exc: SqlExecutionError,
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(LlmGenerationError, handle_llm_generation_error)
    app.add_exception_handler(UnsafeSqlError, handle_unsafe_sql_error)
    app.add_exception_handler(SqlExecutionError, handle_sql_execution_error)
