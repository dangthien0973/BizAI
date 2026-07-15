from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://bizagent:bizagent_dev@localhost:5432/bizagent"
    azure_ai_project_endpoint: str = ""
    azure_ai_key: str = ""
    azure_ai_model: str = "gpt-4o-mini"
    azure_embedding_deployment: str = ""
    azure_openai_endpoint: str = ""

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()