
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment / .env."""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "Universal Data Connector"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # --- Voice / result limits ---
    MAX_VOICE_RESULTS: int = 10
    DEFAULT_PAGE_SIZE: int = 20

    # --- Data paths ---
    DATA_DIR: str = str(BASE_DIR / "data")

    # --- LLM / Google Gemini settings ---
    GOOGLE_API_KEY: str = ""
    GOOGLE_MODEL: str = "gemini-2.5-flash"

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"


settings = Settings()
