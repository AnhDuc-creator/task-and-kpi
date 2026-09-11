from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    KpiUpdateSuggestion,
    SuggestionStatus,
    TaskCompletionSuggestion,
)
from app.schemas import (
    KpiApproveIn,
    KpiSuggestionOut,
    SuggestionContextOut,
    SuggestionQueueOut,
    TaskApproveIn,
    TaskSuggestionOut,
)
from app.services.approval import (
    approve_kpi_suggestion,
    approve_task_suggestion,
    reject_kpi_suggestion,
    reject_task_suggestion,
)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


@router.get("", response_model=SuggestionQueueOut)
def list_suggestions(
    status: SuggestionStatus = Query(default=SuggestionStatus.PENDING),
    db: Session = Depends(get_db),
) -> SuggestionQueueOut:
    kpi_rows = db.scalars(
        select(KpiUpdateSuggestion)
        .where(KpiUpdateSuggestion.status == status)
        .order_by(KpiUpdateSuggestion.id)
    ).all()
    task_rows = db.scalars(
        select(TaskCompletionSuggestion)
        .where(TaskCompletionSuggestion.status == status)
        .order_by(TaskCompletionSuggestion.id)
    ).all()

    return SuggestionQueueOut(
        kpi_updates=[
            SuggestionContextOut(
                id=row.id,
                report_id=row.report_id,
                employee_name=row.report.employee.name,
                week_start=row.report.week_start,
                suggested_kpi_id=row.suggested_kpi_id,
                suggested_delta=row.suggested_delta,
                evidence=row.evidence,
            )
            for row in kpi_rows
        ],
        task_completions=[
            SuggestionContextOut(
                id=row.id,
                report_id=row.report_id,
                employee_name=row.report.employee.name,
                week_start=row.report.week_start,
                suggested_task_id=row.suggested_task_id,
                raw_text=row.raw_text,
            )
            for row in task_rows
        ],
    )


@router.post("/kpi/{suggestion_id}/approve", response_model=KpiSuggestionOut)
def approve_kpi(
    suggestion_id: int, payload: KpiApproveIn, db: Session = Depends(get_db)
) -> KpiUpdateSuggestion:
    return approve_kpi_suggestion(
        db,
        suggestion_id=suggestion_id,
        final_kpi_id=payload.final_kpi_id,
        final_delta=payload.final_delta,
        note=payload.note,
    )


@router.post("/kpi/{suggestion_id}/reject", response_model=KpiSuggestionOut)
def reject_kpi(
    suggestion_id: int, db: Session = Depends(get_db)
) -> KpiUpdateSuggestion:
    return reject_kpi_suggestion(db, suggestion_id=suggestion_id)


@router.post("/task/{suggestion_id}/approve", response_model=TaskSuggestionOut)
def approve_task(
    suggestion_id: int, payload: TaskApproveIn, db: Session = Depends(get_db)
) -> TaskCompletionSuggestion:
    return approve_task_suggestion(
        db, suggestion_id=suggestion_id, final_task_id=payload.final_task_id
    )


@router.post("/task/{suggestion_id}/reject", response_model=TaskSuggestionOut)
def reject_task(
    suggestion_id: int, db: Session = Depends(get_db)
) -> TaskCompletionSuggestion:
    return reject_task_suggestion(db, suggestion_id=suggestion_id)
