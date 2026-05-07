import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    openai_base_url: str = "https://api.deepseek.com"
    openai_api_key: str = ""
    openai_model: str = "deepseek-chat"
    embedding_base_url: str = "http://localhost:8001/v1"
    embedding_api_key: str = "your-embedding-api-key"
    embedding_model: str = "text-embedding-3-small"
    session_store: dict = {}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
