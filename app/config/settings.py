from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="salesdb", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="postgres", alias="DB_PASSWORD")
    ollama_host: str = Field(default="http://ollama:11434", alias="OLLAMA_HOST")
    ollama_model_sql: str = Field(default="qwen2.5-coder:3b", alias="OLLAMA_MODEL_SQL")
    ollama_model_nl: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL_NL")
    ollama_timeout_seconds: float = Field(default=300, alias="OLLAMA_TIMEOUT_SECONDS")
    ollama_temperature_sql: float = Field(default=0, alias="OLLAMA_TEMPERATURE_SQL")
    ollama_temperature_nl: float = Field(default=0.2, alias="OLLAMA_TEMPERATURE_NL")
    ollama_top_p: float = Field(default=1, alias="OLLAMA_TOP_P")
    ollama_num_predict_sql: int = Field(default=512, alias="OLLAMA_NUM_PREDICT_SQL")
    ollama_num_predict_nl: int = Field(default=512, alias="OLLAMA_NUM_PREDICT_NL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
