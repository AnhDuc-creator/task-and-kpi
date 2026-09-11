"""Dependency dùng chung. Tách riêng để test ghi đè được provider."""

from app.config import get_settings
from app.llm.base import LlmProvider
from app.llm.factory import get_provider


def get_llm_provider() -> LlmProvider:
    return get_provider(get_settings())
