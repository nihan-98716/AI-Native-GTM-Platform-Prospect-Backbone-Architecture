import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_url: str
    jwt_secret: str
    jwt_audience: str
    jwt_issuer: str
    cors_origins: list[str]
    rate_limit_per_minute: int
    auto_seed_on_startup: bool
    seed_dir: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "gtm-backbone"),
            environment=os.getenv("APP_ENV", "development"),
            database_url=os.getenv("DATABASE_URL", "postgresql+psycopg://gtm:gtm@postgres:5432/gtm"),
            jwt_secret=os.getenv("JWT_SECRET", "change-me"),
            jwt_audience=os.getenv("JWT_AUDIENCE", "gtm-api"),
            jwt_issuer=os.getenv("JWT_ISSUER", "gtm-local"),
            cors_origins=_as_list(os.getenv("CORS_ORIGINS", "http://localhost:3000")),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")),
            auto_seed_on_startup=_as_bool(os.getenv("AUTO_SEED_ON_STARTUP"), False),
            seed_dir=os.getenv("SEED_DIR", "..\\data"),
        )


_settings_cache: Settings | None = None


def get_settings() -> Settings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = Settings.from_env()
    return _settings_cache

