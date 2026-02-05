from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/neurolink.db"

    # OpenAI settings
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_SUMMARY_MODEL: str = "gpt-4o-mini"

    # Supabase settings
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Processing settings
    AI_PROCESSING_ENABLED: bool = True
    MAX_CONTENT_LENGTH: int = 8000
    EMBEDDING_DIMENSION: int = 1536
    RATE_LIMIT_DELAY: float = 0.5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
