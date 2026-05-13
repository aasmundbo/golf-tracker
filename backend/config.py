from pathlib import Path
from pydantic_settings import BaseSettings

_HERE = Path(__file__).parent

class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/golf.db"
    admin_username: str = "admin"
    admin_password_hash: str = ""
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30
    allowed_origins: str = "*"
    google_client_id: str = ""

    class Config:
        # Project root .env as base; local .env (if present) overrides
        env_file = (str(_HERE.parent / ".env"), ".env")

settings = Settings()
