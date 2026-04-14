"""SpineAgent configuration — loads settings from .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, populated from environment variables / .env file."""

    # Anthropic
    anthropic_api_key: str = ""

    # PostgreSQL
    database_url: str = "postgresql://postgres:postgres@localhost:5432/adventureworks"

    # Embeddings
    embedding_dimensions: int = 1536
    voyage_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
