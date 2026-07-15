from openai import AzureOpenAI
from app.core.config import get_settings

settings = get_settings()

_client: AzureOpenAI | None = None


def get_ai_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_ai_key,
            api_version="2024-05-01-preview",
        )
    return _client