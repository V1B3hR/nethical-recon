"""API configuration."""

import os
from dataclasses import dataclass


@dataclass
class APIConfig:
    """Configuration for the REST API."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 4

    # Security
    secret_key: str = "CHANGE_THIS_IN_PRODUCTION"  # Used for JWT signing
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API
    api_prefix: str = "/api/v1"
    title: str = "Nethical Recon API"
    description: str = "Professional-grade REST API for cybersecurity reconnaissance and threat hunting"
    version: str = "1.0.0"

    # CORS
    cors_origins: list[str] | None = None
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] | None = None
    cors_allow_headers: list[str] | None = None

    # Pagination
    default_page_size: int = 50
    max_page_size: int = 1000

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            reload=os.getenv("API_RELOAD", "false").lower() == "true",
            workers=int(os.getenv("API_WORKERS", "4")),
            secret_key=os.getenv("API_SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION"),
            algorithm=os.getenv("API_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("API_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            api_prefix=os.getenv("API_PREFIX", "/api/v1"),
            title=os.getenv("API_TITLE", "Nethical Recon API"),
            version=os.getenv("API_VERSION", "1.0.0"),
            cors_origins=os.getenv("API_CORS_ORIGINS", "").split(",") if os.getenv("API_CORS_ORIGINS") else None,
            default_page_size=int(os.getenv("API_DEFAULT_PAGE_SIZE", "50")),
            max_page_size=int(os.getenv("API_MAX_PAGE_SIZE", "1000")),
        )
