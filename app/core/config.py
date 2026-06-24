from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ConfigDict
import warnings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Automated Cutover Agent MVP"
    DATABASE_URL: str = "postgresql://postgres:password@db:5432/cutover_db"
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "Cutover-Agent"
    OLLAMA_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid"  # This is what caught the missing declarations!
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Warn about missing critical API keys

settings = Settings()