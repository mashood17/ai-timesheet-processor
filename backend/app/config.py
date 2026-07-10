"""
Centralized application configuration using pydantic-settings.
All environment-driven values live here — nothing else in the codebase
should call os.environ directly. This is what Section 6/2 of the spec require.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Auth
    auth_username: str
    auth_password_hash: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # OCR — Section 2: single config value selects the engine implementation
    ocr_engine: str = "tesseract"
    tesseract_cmd: str | None = None

    # Storage
    storage_dir: str = "./storage"
    session_ttl_minutes: int = 120

    # CORS
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — loaded once per process."""
    return Settings()