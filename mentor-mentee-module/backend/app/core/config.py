from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mentoring Service"
    debug: bool = False

    # Env: DATABASE_URL. Unix socket URL requires Cloud Run --add-cloudsql-instances matching this path,
    # or use a TCP URL (e.g. private IP host:5432).
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:123456@/mentoring?host=/cloudsql/yanc-website%3Aus-central1%3Amentor-mentee-db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    api_v1_prefix: str = "/api/v1"
    jwt_secret: str = Field("secret", validation_alias="JWT_SECRET")
    algorithm: str = "HS256"

    # Comma-separated list of allowed CORS origins for browser clients.
    # Example: "http://localhost:3000,http://127.0.0.1:3000"
    cors_allow_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:4173,"
        "http://127.0.0.1:4173,"
        "http://localhost:5001,"
        "http://127.0.0.1:5001,"
        "https://common-ui-1095720168864-1095720168864.us-central1.run.app,"
        "https://mentee-ui-1095720168864-1095720168864.us-central1.run.app,"
        "https://gamification-service-1095720168864-1095720168864.us-central1.run.app"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
