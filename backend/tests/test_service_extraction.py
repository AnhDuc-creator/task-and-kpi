from datetime import date

import pytest

from app.errors import ConflictError
from app.llm.base import (
    BlockerItem,
    ExtractionError,
    ExtractionResult,
    KpiUpdateItem,
    TaskDoneItem,
)
from app.llm.mock import MockProvider, ScriptedProvider
from app.models import Employee, ExtractionStatus, Kpi, Task, TaskStatus
from app.services.extraction import build_extraction_request, submit_report

WEEK = date(2026, 3, 2)


@pytest.fixture
def seeded(db_session):
    employee = Employee(name="Nguyen Van A", email="a@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()
    task = Task(
        title="Chot hop dong khach X",
        kpi_id=kpi.id,
        assignee_id=employee.id,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    db_session.commit()
    return {"employee": employee, "kpi": kpi, "task": task}


def test_catalog_contains_employee_kpis_and_open_tasks(db_session, seeded):
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="trong",
        provider=MockProvider(),
    )
    request = build_extraction_request(db_session, report)

    assert [item.id for item in request.kpi_catalog] == [seeded["kpi"].id]
    assert [item.id for item in request.task_catalog] == [seeded["task"].id]


def test_done_tasks_are_excluded_from_catalog(db_session, seeded):
    seeded["task"].status = TaskStatus.DONE
    db_session.commit()

    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="trong",
        provider=MockProvider(),
    )
    request = build_extraction_request(db_session, report)

    assert request.task_catalog == []


def test_successful_extraction_creates_suggestions(db_session, seeded):
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text=(
            "Ky them 5 hop dong ky moi.\n"
            "Da chot hop dong khach X.\n"
            "Dang vuong phe duyet phap che."
        ),
        provider=MockProvider(),
    )

    assert report.extraction_status is ExtractionStatus.EXTRACTED
    assert report.provider_name == "mock"
    assert len(report.kpi_suggestions) == 1
    assert report.kpi_suggestions[0].suggested_delta == 5.0
    assert report.kpi_suggestions[0].suggested_kpi_id == seeded["kpi"].id
    assert len(report.task_suggestions) == 1
    assert len(report.blockers) == 1


def test_suggestions_start_pending_with_empty_final_fields(db_session, seeded):
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="Ky them 5 hop dong ky moi.",
        provider=MockProvider(),
    )
    suggestion = report.kpi_suggestions[0]

    assert suggestion.status.value == "pending"
    assert suggestion.final_kpi_id is None
    assert suggestion.final_delta is None


def test_provider_error_marks_report_failed_without_suggestions(db_session, seeded):
    provider = ScriptedProvider(error=ExtractionError("LLM tra ve rac"))
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.FAILED
    assert "rac" in report.extraction_error
    assert report.kpi_suggestions == []
    assert report.task_suggestions == []
    assert report.blockers == []


def test_kpi_id_outside_catalog_marks_report_failed(db_session, seeded):
    """Provider trả kpi_id không có trong catalog -> bao cao failed, khong suggestion."""
    provider = ScriptedProvider(
        result=ExtractionResult(
            tasks_done=[],
            blockers=[],
            kpi_updates=[
                KpiUpdateItem(kpi_id=99999, delta_value=1.0, evidence="ngoai catalog")
            ],
        )
    )
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.FAILED
    assert "99999" in report.extraction_error
    assert report.kpi_suggestions == []
    assert report.blockers == []


def test_task_id_outside_catalog_marks_report_failed(db_session, seeded):
    provider = ScriptedProvider(
        result=ExtractionResult(
            tasks_done=[TaskDoneItem(task_id=99999, description="ngoai catalog")],
            blockers=[],
            kpi_updates=[],
        )
    )
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.FAILED
    assert report.task_suggestions == []


def test_non_finite_delta_marks_report_failed(db_session, seeded):
    """Provider lach Pydantic bang model_construct van bi cong service chan lai."""
    provider = ScriptedProvider(
        result=ExtractionResult.model_construct(
            tasks_done=[],
            blockers=[],
            kpi_updates=[
                KpiUpdateItem.model_construct(
                    kpi_id=seeded["kpi"].id, delta_value=float("inf"), evidence="x"
                )
            ],
        )
    )
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.FAILED
    assert report.kpi_suggestions == []


def test_null_ids_are_persisted_as_null(db_session, seeded):
    provider = ScriptedProvider(
        result=ExtractionResult(
            tasks_done=[TaskDoneItem(task_id=None, description="viec phat sinh")],
            blockers=[BlockerItem(description="thieu nguoi", related_kpi_id=None)],
            kpi_updates=[
                KpiUpdateItem(kpi_id=None, delta_value=3.0, evidence="khong ro KPI")
            ],
        )
    )
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.EXTRACTED
    assert report.kpi_suggestions[0].suggested_kpi_id is None
    assert report.task_suggestions[0].suggested_task_id is None


def test_duplicate_report_raises_conflict(db_session, seeded):
    submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="lan 1",
        provider=MockProvider(),
    )

    with pytest.raises(ConflictError):
        submit_report(
            db_session,
            employee_id=seeded["employee"].id,
            week_start=WEEK,
            raw_text="lan 2",
            provider=MockProvider(),
        )


def test_duplicate_report_does_not_create_second_row(db_session, seeded):
    from app.models import WeeklyReport

    submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="lan 1",
        provider=MockProvider(),
    )
    with pytest.raises(ConflictError):
        submit_report(
            db_session,
            employee_id=seeded["employee"].id,
            week_start=WEEK,
            raw_text="lan 2",
            provider=MockProvider(),
        )

    assert db_session.query(WeeklyReport).count() == 1
