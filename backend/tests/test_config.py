from app.config import Settings


def test_default_provider_is_mock():
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "mock"


def test_default_model_is_sonnet_5():
    settings = Settings(_env_file=None)
    assert settings.anthropic_model == "claude-sonnet-5"
