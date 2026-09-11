"""Duyệt đề xuất. Mỗi hàm là một giao dịch: hoặc cả hai thay đổi cùng được ghi,
hoặc không gì được ghi. Không bao giờ có suggestion `approved` mà sổ cái thiếu dòng.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import (
    Kpi,
    KpiProgressEntry,
    KpiUpdateSuggestion,
    SuggestionStatus,
    Task,
    TaskCompletionSuggestion,
    TaskStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_pending_kpi_suggestion(db: Session, suggestion_id: int) -> KpiUpdateSuggestion:
    suggestion = db.get(KpiUpdateSuggestion, suggestion_id)
    if suggestion is None:
        raise NotFoundError(f"Không tìm thấy đề xuất KPI {suggestion_id}")
    if suggestion.status is not SuggestionStatus.PENDING:
        raise ConflictError("Đề xuất này đã được xử lý")
    return suggestion


def _load_pending_task_suggestion(
    db: Session, suggestion_id: int
) -> TaskCompletionSuggestion:
    suggestion = db.get(TaskCompletionSuggestion, suggestion_id)
    if suggestion is None:
        raise NotFoundError(f"Không tìm thấy đề xuất task {suggestion_id}")
    if suggestion.status is not SuggestionStatus.PENDING:
        raise ConflictError("Đề xuất này đã được xử lý")
    return suggestion


def approve_kpi_suggestion(
    db: Session,
    *,
    suggestion_id: int,
    final_kpi_id: int,
    final_delta: float,
    note: str | None = None,
) -> KpiUpdateSuggestion:
    suggestion = _load_pending_kpi_suggestion(db, suggestion_id)
    if db.get(Kpi, final_kpi_id) is None:
        raise NotFoundError(f"Không tìm thấy KPI {final_kpi_id}")

    try:
        suggestion.final_kpi_id = final_kpi_id
        suggestion.final_delta = final_delta
        suggestion.review_note = note
        suggestion.status = SuggestionStatus.APPROVED
        suggestion.reviewed_at = _utcnow()
        db.add(
            KpiProgressEntry(
                kpi_id=final_kpi_id,
                delta_value=final_delta,
                source_suggestion_id=suggestion.id,
                effective_date=suggestion.report.week_start,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(suggestion)
    return suggestion


def reject_kpi_suggestion(
    db: Session, *, suggestion_id: int, note: str | None = None
) -> KpiUpdateSuggestion:
    suggestion = _load_pending_kpi_suggestion(db, suggestion_id)
    try:
        suggestion.status = SuggestionStatus.REJECTED
        suggestion.review_note = note
        suggestion.reviewed_at = _utcnow()
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(suggestion)
    return suggestion


def approve_task_suggestion(
    db: Session, *, suggestion_id: int, final_task_id: int
) -> TaskCompletionSuggestion:
    suggestion = _load_pending_task_suggestion(db, suggestion_id)
    task = db.get(Task, final_task_id)
    if task is None:
        raise NotFoundError(f"Không tìm thấy task {final_task_id}")

    try:
        suggestion.final_task_id = final_task_id
        suggestion.status = SuggestionStatus.APPROVED
        suggestion.reviewed_at = _utcnow()
        if task.status is not TaskStatus.DONE:
            task.status = TaskStatus.DONE
            task.completed_at = _utcnow()
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(suggestion)
    return suggestion


def reject_task_suggestion(
    db: Session, *, suggestion_id: int
) -> TaskCompletionSuggestion:
    suggestion = _load_pending_task_suggestion(db, suggestion_id)
    try:
        suggestion.status = SuggestionStatus.REJECTED
        suggestion.reviewed_at = _utcnow()
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(suggestion)
    return suggestion
