from datetime import date, datetime

import pytest

from app.errors import ConflictError, NotFoundError
from app.llm.mock import MockProvider
from app.models import (
    Employee,
    Kpi,
    KpiProgressEntry,
    SuggestionStatus,
    Task,
    TaskStatus,
)
from app.services.approval import (
    approve_kpi_suggestion,
    approve_task_suggestion,
    reject_kpi_suggestion,
    reject_task_suggestion,
)
from app.services.extraction import submit_report

WEEK = date(2026, 3, 2)


@pytest.fixture
def report(db_session):
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

    return submit_report(
        db_session,
        employee_id=employee.id,
        week_start=WEEK,
        raw_text="Ky them 5 hop dong ky moi.\nDa chot hop dong khach X.",
        provider=MockProvider(),
    )


def test_approving_writes_ledger_entry(db_session, report):
    suggestion = report.kpi_suggestions[0]

    approve_kpi_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_kpi_id=suggestion.suggested_kpi_id,
        final_delta=5.0,
    )

    entries = db_session.query(KpiProgressEntry).all()
    assert len(entries) == 1
    assert entries[0].delta_value == 5.0
    assert entries[0].source_suggestion_id == suggestion.id
    assert entries[0].effective_date == WEEK


def test_approving_marks_suggestion_approved(db_session, report):
    suggestion = report.kpi_suggestions[0]

    updated = approve_kpi_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_kpi_id=suggestion.suggested_kpi_id,
        final_delta=5.0,
        note="ok",
    )

    assert updated.status is SuggestionStatus.APPROVED
    assert updated.reviewed_at is not None
    assert updated.review_note == "ok"


def test_edited_delta_is_used_not_suggested(db_session, report):
    suggestion = report.kpi_suggestions[0]
    assert suggestion.suggested_delta == 5.0

    updated = approve_kpi_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_kpi_id=suggestion.suggested_kpi_id,
        final_delta=3.0,
    )

    entry = db_session.query(KpiProgressEntry).one()
    assert entry.delta_value == 3.0
    assert updated.suggested_delta == 5.0  # bản gốc không bị ghi đè
    assert updated.final_delta == 3.0


def test_rejecting_writes_no_ledger_entry(db_session, report):
    suggestion = report.kpi_suggestions[0]

    updated = reject_kpi_suggestion(db_session, suggestion_id=suggestion.id)

    assert updated.status is SuggestionStatus.REJECTED
    assert db_session.query(KpiProgressEntry).count() == 0


def test_double_approval_raises_conflict(db_session, report):
    suggestion = report.kpi_suggestions[0]
    approve_kpi_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_kpi_id=suggestion.suggested_kpi_id,
        final_delta=5.0,
    )

    with pytest.raises(ConflictError):
        approve_kpi_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_kpi_id=suggestion.suggested_kpi_id,
            final_delta=5.0,
        )

    assert db_session.query(KpiProgressEntry).count() == 1


def test_approving_rejected_suggestion_raises_conflict(db_session, report):
    suggestion = report.kpi_suggestions[0]
    reject_kpi_suggestion(db_session, suggestion_id=suggestion.id)

    with pytest.raises(ConflictError):
        approve_kpi_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_kpi_id=suggestion.suggested_kpi_id,
            final_delta=5.0,
        )


def test_unknown_suggestion_raises_not_found(db_session, report):
    with pytest.raises(NotFoundError):
        reject_kpi_suggestion(db_session, suggestion_id=999999)


def test_unknown_final_kpi_raises_not_found(db_session, report):
    suggestion = report.kpi_suggestions[0]

    with pytest.raises(NotFoundError):
        approve_kpi_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_kpi_id=999999,
            final_delta=5.0,
        )


def test_failure_mid_approval_rolls_back_everything(db_session, report, monkeypatch):
    """Nếu ghi sổ cái hỏng, suggestion phải quay về pending."""
    suggestion = report.kpi_suggestions[0]

    def explode(*args, **kwargs):
        raise RuntimeError("o dia loi")

    monkeypatch.setattr("app.services.approval.KpiProgressEntry", explode)

    with pytest.raises(RuntimeError):
        approve_kpi_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_kpi_id=suggestion.suggested_kpi_id,
            final_delta=5.0,
        )

    db_session.expire_all()
    assert suggestion.status is SuggestionStatus.PENDING
    assert suggestion.final_delta is None
    assert db_session.query(KpiProgressEntry).count() == 0


def test_approving_task_marks_it_done(db_session, report):
    suggestion = report.task_suggestions[0]

    updated = approve_task_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_task_id=suggestion.suggested_task_id,
    )

    task = db_session.get(Task, suggestion.suggested_task_id)
    assert updated.status is SuggestionStatus.APPROVED
    assert task.status is TaskStatus.DONE
    assert task.completed_at is not None


def test_rejecting_task_leaves_it_untouched(db_session, report):
    suggestion = report.task_suggestions[0]
    task_id = suggestion.suggested_task_id

    reject_task_suggestion(db_session, suggestion_id=suggestion.id)

    task = db_session.get(Task, task_id)
    assert task.status is TaskStatus.TODO
    assert task.completed_at is None


def test_approving_already_done_task_keeps_completed_at(db_session, report):
    suggestion = report.task_suggestions[0]
    task = db_session.get(Task, suggestion.suggested_task_id)
    task.status = TaskStatus.DONE
    task.completed_at = datetime(2026, 1, 1)  # cột là DateTime, không phải Date
    db_session.commit()
    original = task.completed_at

    approve_task_suggestion(
        db_session, suggestion_id=suggestion.id, final_task_id=task.id
    )

    db_session.refresh(task)
    assert task.completed_at == original


def test_double_task_approval_raises_conflict(db_session, report):
    suggestion = report.task_suggestions[0]
    approve_task_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_task_id=suggestion.suggested_task_id,
    )

    with pytest.raises(ConflictError):
        approve_task_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_task_id=suggestion.suggested_task_id,
        )
