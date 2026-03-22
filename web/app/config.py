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

    model_config = ConfigDict(arbitrary_types_allowed=True)

settings = Config()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)