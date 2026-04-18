from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Literal

ENV_FILE = Path(__file__).parent.parent.parent / ".env"

LLMProvider = Literal["gemini", "groq", "openrouter"]


class Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    llm_provider: LLMProvider = "groq"

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")

    def active_key(self) -> str:
        return {
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_key,
            "openrouter": self.openrouter_api_key,
        }.get(self.llm_provider, "")

    def is_configured(self) -> bool:
        return bool(self.active_key().strip())

    def reload(self) -> None:
        fresh = Settings()
        self.gemini_api_key = fresh.gemini_api_key
        self.groq_api_key = fresh.groq_api_key
        self.openrouter_api_key = fresh.openrouter_api_key
        self.llm_provider = fresh.llm_provider


settings = Settings()
