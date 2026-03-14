import os
from pathlib import Path
from pydantic import BaseModel

class Config(BaseModel):
    APP_NAME: str = "SocialGrowthAI"
    VERSION: str = "0.1.0"
    DATA_DIR: Path = Path("data")
    DB_NAME: str = "social_growth.db"
    LOG_LEVEL: str = "INFO"
    HEADLESS: bool = False  # For Playwright

    # AI Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:7b-instruct"

    class Config:
        arbitrary_types_allowed = True

settings = Config()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
