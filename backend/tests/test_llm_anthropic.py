import pytest

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import (
    ExtractionError,
    ExtractionRequest,
    ExtractionResult,
    KpiCatalogItem,
    KpiUpdateItem,
    TaskCatalogItem,
)
from app.llm.prompt import build_user_prompt

REQUEST = ExtractionRequest(
    report_text="Ky them 5 hop dong.",
    kpi_catalog=[
        KpiCatalogItem(id=7, name="Hop dong ky moi", unit="hop dong", target_value=100.0)
    ],
    task_catalog=[TaskCatalogItem(id=12, title="Chot hop dong khach X")],
)


class FakeResponse:
    def __init__(self, parsed_output=None, stop_reason="end_turn"):
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.last_kwargs = None

    def parse(self, **kwargs):
        self.last_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.messages = FakeMessages(response=response, error=error)


def test_user_prompt_contains_catalog_and_report():
    prompt = build_user_prompt(REQUEST)
    assert "Hop dong ky moi" in prompt
    assert "Chot hop dong khach X" in prompt
    assert "Ky them 5 hop dong." in prompt
    assert "7" in prompt


def test_returns_parsed_output():
    expected = ExtractionResult(
        tasks_done=[],
        kpi_updates=[KpiUpdateItem(kpi_id=7, delta_value=5.0, evidence="Ky them 5")],
        blockers=[],
    )
    client = FakeClient(response=FakeResponse(parsed_output=expected))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    assert provider.extract(REQUEST) == expected


def test_sends_configured_model_and_output_format():
    expected = ExtractionResult(tasks_done=[], kpi_updates=[], blockers=[])
    client = FakeClient(response=FakeResponse(parsed_output=expected))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    provider.extract(REQUEST)

    kwargs = client.messages.last_kwargs
    assert kwargs["model"] == "claude-sonnet-5"
    assert kwargs["output_format"] is ExtractionResult


def test_refusal_becomes_extraction_error():
    client = FakeClient(response=FakeResponse(parsed_output=None, stop_reason="refusal"))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    with pytest.raises(ExtractionError):
        provider.extract(REQUEST)


def test_missing_parsed_output_becomes_extraction_error():
    client = FakeClient(response=FakeResponse(parsed_output=None))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    with pytest.raises(ExtractionError):
        provider.extract(REQUEST)


def test_sdk_error_becomes_extraction_error():
    client = FakeClient(error=RuntimeError("mang loi"))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    with pytest.raises(ExtractionError):
        provider.extract(REQUEST)
