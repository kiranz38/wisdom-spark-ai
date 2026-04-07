from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Wisdom Spark AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/wisdom_spark"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Embeddings (OpenAI-compatible endpoint)
    embedding_api_key: str = ""
    embedding_api_base: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # API
    api_prefix: str = "/v1"
    default_page_size: int = 20
    max_page_size: int = 100

    # Rate limits
    free_requests_per_day: int = 500

    model_config = {"env_file": ".env", "env_prefix": "WISDOM_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
