import pytest

from app.config import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.factory import get_provider
from app.llm.mock import MockProvider


def test_default_settings_give_mock_provider():
    provider = get_provider(Settings(_env_file=None))
    assert isinstance(provider, MockProvider)


def test_anthropic_provider_selected_when_configured():
    settings = Settings(
        _env_file=None, llm_provider="anthropic", anthropic_api_key="test-key"
    )
    assert isinstance(get_provider(settings), AnthropicProvider)


def test_anthropic_without_api_key_is_rejected():
    settings = Settings(_env_file=None, llm_provider="anthropic", anthropic_api_key=None)
    with pytest.raises(ValueError):
        get_provider(settings)


def test_unknown_provider_is_rejected():
    settings = Settings(_env_file=None, llm_provider="khong-ton-tai")
    with pytest.raises(ValueError):
        get_provider(settings)
