import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict

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

    model_config = ConfigDict(arbitrary_types_allowed=True)

settings = Config(
    APP_NAME=os.getenv("APP_NAME", "SocialGrowthAI"),
    VERSION=os.getenv("VERSION", "0.1.0"),
    DATA_DIR=Path(os.getenv("DATA_DIR", "data")),
    DB_NAME=os.getenv("DB_NAME", "social_growth.db"),
    LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
    HEADLESS=os.getenv("HEADLESS", "false").lower() == "true",
    OPENROUTER_BASE_URL=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    OPENROUTER_MODEL=os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo"),
    OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY", ""),
    CORS_ALLOWED_ORIGINS=os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000"),
    RUST_SERVICE_URL=os.getenv("RUST_SERVICE_URL", "http://localhost:8081"),
    RUST_SERVICE_TIMEOUT_SECONDS=float(os.getenv("RUST_SERVICE_TIMEOUT_SECONDS", "5")),
    DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///data/social_growth.db"),
)

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
