from datetime import date

import pytest

from app.errors import ConflictError
from app.llm.base import ExtractionError, ExtractionResult
from app.llm.mock import MockProvider, ScriptedProvider
from app.models import (
    Blocker,
    Employee,
    ExtractionStatus,
    Kpi,
    KpiUpdateSuggestion,
    SuggestionStatus,
    Task,
    TaskCompletionSuggestion,
    TaskStatus,
)
from app.services.extraction import reextract_report, submit_report

WEEK = date(2026, 3, 2)
REPORT_TEXT = (
    "Ky them 5 hop dong ky moi.\n"
    "Da chot hop dong khach X.\n"
    "Dang vuong phe duyet phap che."
)


@pytest.fixture
def seeded(db_session):
    employee = Employee(name="A", email="a@example.com")
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


def make_report(db_session, seeded, provider):
    return submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text=REPORT_TEXT,
        provider=provider,
    )


def test_failed_report_can_be_reextracted(db_session, seeded):
    report = make_report(
        db_session, seeded, ScriptedProvider(error=ExtractionError("hong"))
    )
    assert report.extraction_status is ExtractionStatus.FAILED
    assert report.extraction_error is not None

    report = reextract_report(db_session, report, MockProvider())

    assert report.extraction_status is ExtractionStatus.EXTRACTED
    assert report.extraction_error is None
    assert len(report.kpi_suggestions) == 1


def test_extracted_report_without_approvals_can_be_reextracted(db_session, seeded):
    """Đánh dấu dòng cũ rồi kiểm dòng còn lại không mang dấu đó.

    Không so sánh id: SQLite cấp lại khoá chính khi bảng bị xoá sạch, nên
    id trùng nhau là chuyện bình thường và không nói lên điều gì.
    """
    report = make_report(db_session, seeded, MockProvider())
    report.kpi_suggestions[0].evidence = "DAU VET CU"
    db_session.commit()

    report = reextract_report(db_session, report, MockProvider())

    assert len(report.kpi_suggestions) == 1
    assert report.kpi_suggestions[0].evidence != "DAU VET CU"


def test_reextraction_deletes_pending_suggestions(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())

    reextract_report(
        db_session,
        report,
        ScriptedProvider(
            result=ExtractionResult(tasks_done=[], kpi_updates=[], blockers=[])
        ),
    )

    assert db_session.query(KpiUpdateSuggestion).count() == 0
    assert db_session.query(TaskCompletionSuggestion).count() == 0


def test_reextraction_keeps_rejected_suggestions(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    rejected = report.kpi_suggestions[0]
    rejected.status = SuggestionStatus.REJECTED
    db_session.commit()
    rejected_id = rejected.id

    reextract_report(db_session, report, MockProvider())

    survivor = db_session.get(KpiUpdateSuggestion, rejected_id)
    assert survivor is not None
    assert survivor.status is SuggestionStatus.REJECTED


def test_reextraction_recreates_blockers(db_session, seeded):
    """Blocker cũ bị xoá và tạo lại — kiểm bằng nội dung, không bằng id."""
    report = make_report(db_session, seeded, MockProvider())
    report.blockers[0].description = "DAU VET CU"
    db_session.commit()

    report = reextract_report(db_session, report, MockProvider())

    assert len(report.blockers) == 1
    assert report.blockers[0].description != "DAU VET CU"
    assert db_session.query(Blocker).count() == 1


def test_approved_kpi_suggestion_blocks_reextraction(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    report.kpi_suggestions[0].status = SuggestionStatus.APPROVED
    db_session.commit()

    with pytest.raises(ConflictError):
        reextract_report(db_session, report, MockProvider())


def test_approved_task_suggestion_also_blocks_reextraction(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    report.task_suggestions[0].status = SuggestionStatus.APPROVED
    db_session.commit()

    with pytest.raises(ConflictError):
        reextract_report(db_session, report, MockProvider())


def test_blocked_reextraction_changes_nothing(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    report.task_suggestions[0].status = SuggestionStatus.APPROVED
    db_session.commit()
    kpi_ids_before = {s.id for s in report.kpi_suggestions}
    blocker_ids_before = {b.id for b in report.blockers}

    with pytest.raises(ConflictError):
        reextract_report(db_session, report, MockProvider())

    db_session.refresh(report)
    assert {s.id for s in report.kpi_suggestions} == kpi_ids_before
    assert {b.id for b in report.blockers} == blocker_ids_before
