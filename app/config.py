import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict

class Config(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "SocialGrowthAI")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    DB_NAME: str = os.getenv("DB_NAME", "social_growth.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HEADLESS: bool = os.getenv("HEADLESS", "False").lower() in ("1", "true", "yes")

    # AI Settings
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000")
    RUST_SERVICE_URL: str = os.getenv("RUST_SERVICE_URL", "http://127.0.0.1:8081")
    RUST_SERVICE_TIMEOUT_SECONDS: float = float(os.getenv("RUST_SERVICE_TIMEOUT_SECONDS", "5.0"))
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/social_growth.db")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")
    REDIRECT_ROOT_TO_FRONTEND: bool = os.getenv("REDIRECT_ROOT_TO_FRONTEND", "False").lower() in ("1", "true", "yes")
    API_KEY: str = os.getenv("API_KEY", "super-secret-api-key")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_USER_IDS: str = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")

    model_config = ConfigDict(arbitrary_types_allowed=True)

settings = Config()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
