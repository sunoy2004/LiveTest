from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:123456@/user_db?host=/cloudsql/yanc-website%3Aus-central1%3Amentor-mentee-db"
    redis_url: str = "redis://localhost:6379/0"
    user_service_url: str = "http://localhost:8000"
    internal_api_token: str = "change-me-in-production"
    jwt_secret: str = "secret"
    ai_trust_gateway_headers: bool = False

    embedding_provider: Literal["opensource", "vertex"] = "opensource"
    use_vertex: bool = False
    opensource_model: str = "sentence-transformers/all-mpnet-base-v2"
    vertex_embedding_model: str = "text-embedding-004"
    gcp_location: str = "us-central1"

    recommendation_engine: Literal["pgvector", "graph"] = "pgvector"
    recommendation_cache_ttl: int = 300
    hybrid_scoring: bool = False
    rec_cache_key_version: str = "v1"

    embedding_dim: int = 768

    @property
    def use_vertex_provider(self) -> bool:
        return self.embedding_provider == "vertex" and self.use_vertex


@lru_cache
def get_settings() -> Settings:
    return Settings()
