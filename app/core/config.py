from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Automated Cutover Agent MVP"
    DATABASE_URL: str = "postgresql://postgres:password@db:5432/cutover_db"
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid"  # This is what caught the missing declarations!
    )

settings = Settings()