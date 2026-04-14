import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict

def _getenv_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default

def _getenv_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def _getenv_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default

class Config(BaseModel):
    APP_NAME: str = "SocialGrowthAI"
    VERSION: str = "0.1.0"
    DATA_DIR: Path = Path("data")
    DB_NAME: str = "social_growth.db"
    LOG_LEVEL: str = "INFO"
    HEADLESS: bool = False  # For Playwright

    # AI Settings
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-3.5-turbo"
    OPENROUTER_API_KEY: str = ""
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"
    RUST_SERVICE_URL: str = "http://localhost:8081"
    RUST_SERVICE_TIMEOUT_SECONDS: float = 5.0
    DATABASE_URL: str = "sqlite:///data/social_growth.db"
    FRONTEND_URL: str = ""
    REDIRECT_ROOT_TO_FRONTEND: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

settings = Config(
    APP_NAME=_getenv_str("APP_NAME", "SocialGrowthAI"),
    VERSION=_getenv_str("VERSION", "0.1.0"),
    DATA_DIR=Path(_getenv_str("DATA_DIR", "data")),
    DB_NAME=_getenv_str("DB_NAME", "social_growth.db"),
    LOG_LEVEL=_getenv_str("LOG_LEVEL", "INFO"),
    HEADLESS=_getenv_bool("HEADLESS", False),
    OPENROUTER_BASE_URL=_getenv_str("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    OPENROUTER_MODEL=_getenv_str("OPENROUTER_MODEL", "openai/gpt-3.5-turbo"),
    OPENROUTER_API_KEY=_getenv_str("OPENROUTER_API_KEY", ""),
    CORS_ALLOWED_ORIGINS=_getenv_str("CORS_ALLOWED_ORIGINS", "http://localhost:3000"),
    RUST_SERVICE_URL=_getenv_str("RUST_SERVICE_URL", "http://localhost:8081"),
    RUST_SERVICE_TIMEOUT_SECONDS=_getenv_float("RUST_SERVICE_TIMEOUT_SECONDS", 5.0),
    DATABASE_URL=_getenv_str("DATABASE_URL", "sqlite:///data/social_growth.db"),
    FRONTEND_URL=_getenv_str("FRONTEND_URL", ""),
    REDIRECT_ROOT_TO_FRONTEND=_getenv_bool("REDIRECT_ROOT_TO_FRONTEND", False),
)

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
