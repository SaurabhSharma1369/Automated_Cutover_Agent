from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Automated Cutover Agent MVP"
    DATABASE_URL: str = "postgresql://postgres:password@db:5432/cutover_db"
    GMAIL_API_KEY: str = "placeholder_token"

    model_config = ConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()