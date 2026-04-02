from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Comma-separated list of allowed CORS origins.
    # Use "*" only for local development; always restrict in production.
    cors_origins: str = "http://localhost:5173,http://localhost:3000, http://localhost:5174"

    raw_data_path: str = "data/raw"
    processed_data_path: str = "data/processed"
    spacy_model: str = "en_core_web_sm"

    def get_cors_origins(self) -> list[str]:
        """Return the parsed list of allowed CORS origins.

        Returns:
            List of origin strings split from the comma-separated config value.
        """
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
