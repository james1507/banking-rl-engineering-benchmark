from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://localhost/banking_lab"
    jwt_secret: str = Field(min_length=32)
    app_env: str = "local"
    jwt_issuer: str = "banking-lab"
    jwt_audience: str = "banking-lab-api"
    access_seconds: int = 900
    refresh_seconds: int = 604800
    pool_size: int = 8
    otlp_endpoint: str | None = None


@lru_cache
def settings() -> Settings:
    return Settings()
