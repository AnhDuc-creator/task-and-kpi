from app.config import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LlmProvider
from app.llm.mock import MockProvider


def get_provider(settings: Settings) -> LlmProvider:
    if settings.llm_provider == "mock":
        return MockProvider()
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("LLM_PROVIDER=anthropic nhưng thiếu ANTHROPIC_API_KEY")
        return AnthropicProvider(
            api_key=settings.anthropic_api_key, model=settings.anthropic_model
        )
    raise ValueError(f"LLM_PROVIDER không hợp lệ: {settings.llm_provider}")
