import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.api.exception_handlers import register_exception_handlers
from app.api.v1.ask_router import router as ask_router
from app.config.logging import configure_logging
from app.db.connection import connect

configure_logging()

app = FastAPI(title="local-sales-text-to-sql")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(ask_router)
register_exception_handlers(app)


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db-health")
def db_health() -> dict[str, str]:
    try:
        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except (psycopg.Error, ValidationError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Database connectivity check failed. Verify DB_* environment variables and network access.",
        ) from exc

    return {"database": "ok"}
