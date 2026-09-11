import pytest

from app.llm.base import (
    ExtractionError,
    ExtractionRequest,
    ExtractionResult,
    KpiCatalogItem,
    TaskCatalogItem,
)
from app.llm.mock import MockProvider, ScriptedProvider

CATALOG_KPIS = [
    KpiCatalogItem(id=7, name="Hop dong ky moi", unit="hop dong", target_value=100.0)
]
CATALOG_TASKS = [TaskCatalogItem(id=12, title="Chot hop dong khach X")]


def make_request(text: str) -> ExtractionRequest:
    return ExtractionRequest(
        report_text=text, kpi_catalog=CATALOG_KPIS, task_catalog=CATALOG_TASKS
    )


def test_matches_kpi_by_name_and_extracts_number():
    request = make_request("Tuan nay ky them 5 hop dong ky moi.")
    result = MockProvider().extract(request)
    assert len(result.kpi_updates) == 1
    assert result.kpi_updates[0].kpi_id == 7
    assert result.kpi_updates[0].delta_value == 5.0


def test_kpi_name_without_number_produces_no_update():
    request = make_request("Da trao doi ve hop dong ky moi voi khach.")
    result = MockProvider().extract(request)
    assert result.kpi_updates == []


def test_matches_task_by_title():
    request = make_request("Da chot hop dong khach X trong tuan.")
    result = MockProvider().extract(request)
    assert len(result.tasks_done) == 1
    assert result.tasks_done[0].task_id == 12


def test_detects_blocker_line():
    request = make_request("Dang vuong phe duyet tu phong phap che.")
    result = MockProvider().extract(request)
    assert len(result.blockers) == 1
    assert "phap che" in result.blockers[0].description


def test_unmatched_line_produces_nothing():
    request = make_request("Tham gia hop giao ban dau tuan.")
    result = MockProvider().extract(request)
    assert result.kpi_updates == []
    assert result.tasks_done == []
    assert result.blockers == []


def test_is_deterministic():
    request = make_request("Ky them 5 hop dong ky moi.")
    provider = MockProvider()
    assert provider.extract(request) == provider.extract(request)


def test_scripted_provider_returns_canned_result():
    canned = ExtractionResult(tasks_done=[], kpi_updates=[], blockers=[])
    assert ScriptedProvider(result=canned).extract(make_request("x")) is canned


def test_scripted_provider_raises_configured_error():
    provider = ScriptedProvider(error=ExtractionError("loi gia lap"))
    with pytest.raises(ExtractionError):
        provider.extract(make_request("x"))
