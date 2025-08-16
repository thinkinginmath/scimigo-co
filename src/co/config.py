"""Configuration settings for the Curriculum Orchestrator."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_prefix="CO_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    # Application
    app_name: str = "Scimigo Curriculum Orchestrator"
    debug: bool = False
    environment: str = "development"
    
    # Database
    # Default to Postgres; tests may override via CO_DB_URL
    db_url: str = "postgresql+asyncpg://localhost/scimigo_co"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # External Services
    api_base: str = "https://api.scimigo.com"
    eval_base: str = "https://eval.scimigo.com"
    problem_bank_base: str = "https://problems.scimigo.com"
    tutor_base: str = "https://tutor.scimigo.com"
    
    # Auth
    jwt_issuer: str = "api.scimigo.com"
    jwt_audience: str = "scimigo"
    jwt_algorithm: str = "RS256"
    jwt_public_key: Optional[str] = None
    
    # CORS
    cors_origins: list[str] = [
        "https://coding.scimigo.com",
        "https://app.scimigo.com",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    
    # Rate Limiting
    rate_limit_requests: int = 60
    rate_limit_window: int = 60  # seconds
    max_concurrent_sse: int = 2
    
    # Personalization weights
    weight_weakness: float = 0.4
    weight_novelty: float = 0.2
    weight_difficulty: float = 0.25
    weight_recency: float = 0.15
    
    # Spaced repetition buckets (days)
    review_buckets: list[int] = [1, 3, 7, 21]
    
    # OpenTelemetry
    otel_enabled: bool = False
    otel_endpoint: Optional[str] = None
    otel_service_name: str = "curriculum-orchestrator"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
