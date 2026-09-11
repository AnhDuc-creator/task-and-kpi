import pytest
from pydantic import ValidationError

from app.llm.base import (
    ExtractionError,
    ExtractionRequest,
    ExtractionResult,
    KpiCatalogItem,
    KpiUpdateItem,
    TaskCatalogItem,
    validate_extraction_result,
)

REQUEST = ExtractionRequest(
    report_text="bat ky",
    kpi_catalog=[
        KpiCatalogItem(id=7, name="Hop dong ky moi", unit="hop dong", target_value=100.0)
    ],
    task_catalog=[TaskCatalogItem(id=12, title="Chot hop dong khach X")],
)


def test_parses_valid_payload():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [{"task_id": 12, "description": "xong"}],
            "kpi_updates": [
                {"kpi_id": 7, "delta_value": 5, "evidence": "ky them 5"}
            ],
            "blockers": [{"description": "thieu nguoi", "related_kpi_id": 7}],
        }
    )
    assert result.kpi_updates[0].delta_value == 5.0
    assert result.tasks_done[0].task_id == 12


def test_null_ids_are_allowed():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [{"task_id": None, "description": "viec phat sinh"}],
            "kpi_updates": [
                {"kpi_id": None, "delta_value": 3, "evidence": "khong ro KPI"}
            ],
            "blockers": [],
        }
    )
    assert result.kpi_updates[0].kpi_id is None


def test_missing_required_key_is_rejected():
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate({"tasks_done": [], "kpi_updates": []})


def test_infinite_delta_is_rejected():
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate(
            {
                "tasks_done": [],
                "blockers": [],
                "kpi_updates": [
                    {"kpi_id": 7, "delta_value": float("inf"), "evidence": "x"}
                ],
            }
        )


def test_unknown_kpi_id_is_rejected():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [],
            "blockers": [],
            "kpi_updates": [{"kpi_id": 999, "delta_value": 1, "evidence": "x"}],
        }
    )
    with pytest.raises(ExtractionError) as excinfo:
        validate_extraction_result(result, REQUEST)
    assert "999" in str(excinfo.value)


def test_unknown_task_id_is_rejected():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [{"task_id": 999, "description": "x"}],
            "blockers": [],
            "kpi_updates": [],
        }
    )
    with pytest.raises(ExtractionError):
        validate_extraction_result(result, REQUEST)


def test_unknown_related_kpi_id_in_blocker_is_rejected():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [],
            "blockers": [{"description": "x", "related_kpi_id": 999}],
            "kpi_updates": [],
        }
    )
    with pytest.raises(ExtractionError):
        validate_extraction_result(result, REQUEST)


def test_known_ids_pass_validation():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [{"task_id": 12, "description": "x"}],
            "blockers": [{"description": "y", "related_kpi_id": 7}],
            "kpi_updates": [{"kpi_id": 7, "delta_value": 2, "evidence": "z"}],
        }
    )
    validate_extraction_result(result, REQUEST)  # không ném lỗi


def test_gate_catches_infinite_delta_that_bypassed_pydantic():
    """Provider dựng object bằng model_construct vẫn không lách được cổng."""
    result = ExtractionResult.model_construct(
        tasks_done=[],
        blockers=[],
        kpi_updates=[
            KpiUpdateItem.model_construct(
                kpi_id=7, delta_value=float("inf"), evidence="x"
            )
        ],
    )
    with pytest.raises(ExtractionError):
        validate_extraction_result(result, REQUEST)


def test_gate_catches_nan_delta_that_bypassed_pydantic():
    result = ExtractionResult.model_construct(
        tasks_done=[],
        blockers=[],
        kpi_updates=[
            KpiUpdateItem.model_construct(
                kpi_id=7, delta_value=float("nan"), evidence="x"
            )
        ],
    )
    with pytest.raises(ExtractionError):
        validate_extraction_result(result, REQUEST)
