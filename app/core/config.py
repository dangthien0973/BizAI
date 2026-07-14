from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://bizagent:bizagent_dev@localhost:5432/bizagent"

    # Azure AI Foundry
    # Tên biến phải khớp với tên trong .env (không phân biệt hoa thường)
    azure_ai_project_endpoint: str = ""
    azure_ai_key: str = ""
    azure_ai_model: str = "gpt-4o-mini"
    azure_embedding_deployment: str = ""

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()