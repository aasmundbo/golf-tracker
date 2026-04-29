from pathlib import Path
from pydantic_settings import BaseSettings

_HERE = Path(__file__).parent

class Settings(BaseSettings):
    golf_course_api_key: str = ""
    database_url: str = "sqlite:///./data/golf.db"

    class Config:
        # Project root .env as base; local .env (if present) overrides
        env_file = (str(_HERE.parent / ".env"), ".env")

settings = Settings()
