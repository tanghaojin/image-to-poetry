from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "见景寻诗 API"
    app_version: str = "0.1.0"
    environment: str = "local"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = (
        "postgresql+asyncpg://img2poetry:img2poetry@localhost:5432/img2poetry"
    )
    redis_url: str = "redis://localhost:6379/0"
    redis_key_prefix: str = "img2poetry"
    cors_origins: str = "http://localhost:3100"

    rate_limit_enabled: bool = True
    rate_limit_daily: int = 100
    rate_limit_timezone: str = "Asia/Hong_Kong"
    fingerprint_hash_secret: str = "local-development-only-change-me"

    google_ai_api_key: str = ""
    big_model_api_key: str = ""
    vision_model_order: str = (
        "gemini-3.7-flash,gemini-3.6-flash,"
        "glm-4.6v-flash,glm-4.1v-thinking-flash"
    )
    image_max_bytes: int = 10 * 1024 * 1024
    image_max_edge: int = 1600
    image_jpeg_quality: int = 85
    vision_connect_timeout: float = 5.0
    vision_read_timeout: float = 20.0
    vision_total_timeout: float = 45.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def vision_models(self) -> list[str]:
        return [item.strip() for item in self.vision_model_order.split(",") if item.strip()]

    @field_validator("rate_limit_daily")
    @classmethod
    def validate_daily_limit(cls, value: int) -> int:
        if value < 1:
            raise ValueError("RATE_LIMIT_DAILY must be positive")
        return value

    @field_validator("image_max_bytes", "image_max_edge", "image_jpeg_quality")
    @classmethod
    def validate_image_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("image limits must be positive")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
