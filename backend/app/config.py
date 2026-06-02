from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://da_agent:da_agent@localhost:5432/da_agent"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    # mock | openai
    llm_provider: str = "mock"
    cors_origins: str = "http://localhost:5173"


settings = Settings()
