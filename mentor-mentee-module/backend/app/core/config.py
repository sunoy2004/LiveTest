from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mentoring Service"
    debug: bool = False

    # Env: DATABASE_URL (pydantic-settings default for field database_url)
    database_url: str = "postgresql+asyncpg://postgres:123456@/mentoring?host=/cloudsql/yanc-website%3Aus-central1%3Amentor-mentee-db"

    api_v1_prefix: str = "/api/v1"

    # Comma-separated list of allowed CORS origins for browser clients.
    # Example: "http://localhost:3000,http://127.0.0.1:3000"
    cors_allow_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://common-ui-1095720168864-1095720168864.us-central1.run.app,"
        "https://mentee-ui-1095720168864-1095720168864.us-central1.run.app,"
        "https://gamification-service-1095720168864-1095720168864.us-central1.run.app"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
