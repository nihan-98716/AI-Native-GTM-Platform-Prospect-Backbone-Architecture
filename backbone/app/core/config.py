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
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    integration_default_provider: str = "apollo"
    integration_rate_limit_per_minute: int = 60
    integration_retry_max_attempts: int = 3
    integration_retry_backoff_ms: int = 50
    integration_circuit_breaker_threshold: int = 3
    integration_circuit_breaker_open_seconds: int = 60
    integration_providers: list[str] | None = None
    workflow_queue_threshold: int = 50
    workflow_concurrent_limit: int = 4
    workflow_retry_max_attempts: int = 2
    workflow_job_timeout_seconds: int = 300
    workflow_inline_execution: bool = True
    workflow_redis_url: str | None = None
    apollo_api_key: str | None = None
    apollo_base_url: str = "https://api.apollo.io"
    apollo_allowed_hosts: list[str] | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "gtm-backbone"),
            environment=os.getenv("APP_ENV", "development"),
            database_url=os.getenv("DATABASE_URL", "postgresql+psycopg://gtm:gtm@127.0.0.1:5432/gtm"),
            jwt_secret=os.getenv("JWT_SECRET", "change-me"),
            jwt_audience=os.getenv("JWT_AUDIENCE", "gtm-api"),
            jwt_issuer=os.getenv("JWT_ISSUER", "gtm-local"),
            cors_origins=_as_list(os.getenv("CORS_ORIGINS", "http://localhost:3000")),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")),
            auto_seed_on_startup=_as_bool(os.getenv("AUTO_SEED_ON_STARTUP"), False),
            seed_dir=os.getenv("SEED_DIR", "..\\data"),
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4.1-mini"),
            llm_api_key=os.getenv("OPENAI_API_KEY"),
            llm_base_url=os.getenv("OPENAI_BASE_URL"),
            integration_default_provider=os.getenv("INTEGRATION_DEFAULT_PROVIDER", "apollo"),
            integration_rate_limit_per_minute=int(os.getenv("INTEGRATION_RATE_LIMIT_PER_MINUTE", "60")),
            integration_retry_max_attempts=int(os.getenv("INTEGRATION_RETRY_MAX_ATTEMPTS", "3")),
            integration_retry_backoff_ms=int(os.getenv("INTEGRATION_RETRY_BACKOFF_MS", "50")),
            integration_circuit_breaker_threshold=int(os.getenv("INTEGRATION_CIRCUIT_BREAKER_THRESHOLD", "3")),
            integration_circuit_breaker_open_seconds=int(os.getenv("INTEGRATION_CIRCUIT_BREAKER_OPEN_SECONDS", "60")),
            integration_providers=_as_list(os.getenv("INTEGRATION_PROVIDERS", "apollo")),
            workflow_queue_threshold=int(os.getenv("WORKFLOW_QUEUE_THRESHOLD", "50")),
            workflow_concurrent_limit=int(os.getenv("WORKFLOW_CONCURRENT_LIMIT", "4")),
            workflow_retry_max_attempts=int(os.getenv("WORKFLOW_RETRY_MAX_ATTEMPTS", "2")),
            workflow_job_timeout_seconds=int(os.getenv("WORKFLOW_JOB_TIMEOUT_SECONDS", "300")),
            workflow_inline_execution=_as_bool(os.getenv("WORKFLOW_INLINE_EXECUTION"), True),
            workflow_redis_url=os.getenv("WORKFLOW_REDIS_URL"),
            apollo_api_key=os.getenv("APOLLO_API_KEY"),
            apollo_base_url=os.getenv("APOLLO_BASE_URL", "https://api.apollo.io"),
            apollo_allowed_hosts=_as_list(os.getenv("APOLLO_ALLOWED_HOSTS", "api.apollo.io,apollo.io")),
        )


_settings_cache: Settings | None = None


def get_settings() -> Settings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = Settings.from_env()
    return _settings_cache

