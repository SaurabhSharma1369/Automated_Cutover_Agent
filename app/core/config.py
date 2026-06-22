from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import warnings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Automated Cutover Agent MVP"
    DATABASE_URL: str = "postgresql://postgres:password@db:5432/cutover_db"
    GMAIL_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "Cutover-Agent"
    OLLAMA_API_KEY: str = ""

    model_config = ConfigDict(case_sensitive=True, env_file=".env")

    def __init__(self, **data):
        super().__init__(**data)
        # Warn about missing critical API keys
        if not self.GOOGLE_API_KEY or self.GOOGLE_API_KEY == "your_google_api_key_here":
            warnings.warn("⚠️  GOOGLE_API_KEY is not configured. GenAI features will not work.", RuntimeWarning)
        if not self.GMAIL_API_KEY or self.GMAIL_API_KEY == "your_gmail_api_key_here":
            warnings.warn("⚠️  GMAIL_API_KEY is not configured. Email features will not work.", RuntimeWarning)

settings = Settings()