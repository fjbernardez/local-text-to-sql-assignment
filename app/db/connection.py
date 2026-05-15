import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from app.config.settings import get_settings


def connect() -> Connection:
    settings = get_settings()
    return psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        row_factory=dict_row,
        connect_timeout=5,
    )
