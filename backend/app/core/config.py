from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FORPAY_", env_file=".env", extra="ignore")

    app_name: str = "ForPay"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://forpay:forpay@localhost:5432/forpay"
    redis_url: str = "redis://localhost:6379/0"
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173"
    session_secret: str = "change-this-in-development"
    admin_token: str = "local-admin-token"
    monitor_token: str = "local-monitor-token"
    order_ttl_minutes: int = 15
    amount_suffix_cents: int = 1
    max_body_mb: int = 8
    rate_limit_per_minute: int = 60
    update_manifest_url: str | None = None
    update_public_key: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def validate_production_secrets(self) -> None:
        if self.environment == "development":
            return
        defaults = {"change-this-in-development", "local-development-only", "local-admin-token", "local-monitor-token"}
        if self.session_secret in defaults or self.admin_token in defaults or self.monitor_token in defaults:
            raise RuntimeError("生产环境必须修改 FORPAY_SESSION_SECRET、FORPAY_ADMIN_TOKEN 和 FORPAY_MONITOR_TOKEN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
