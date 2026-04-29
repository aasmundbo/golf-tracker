from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    golf_course_api_key: str = ""
    database_url: str = "sqlite:///./data/golf.db"

    class Config:
        env_file = ".env"

settings = Settings()
