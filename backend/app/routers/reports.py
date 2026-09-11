from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_llm_provider
from app.errors import NotFoundError
from app.llm.base import LlmProvider
from app.models import Employee, WeeklyReport
from app.schemas import ReportCreate, ReportOut
from app.services.extraction import reextract_report, submit_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)) -> list[WeeklyReport]:
    return list(
        db.scalars(select(WeeklyReport).order_by(WeeklyReport.id.desc())).all()
    )


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    provider: LlmProvider = Depends(get_llm_provider),
) -> WeeklyReport:
    if db.get(Employee, payload.employee_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {payload.employee_id}")
    return submit_report(
        db,
        employee_id=payload.employee_id,
        week_start=payload.week_start,
        raw_text=payload.raw_text,
        provider=provider,
    )


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)) -> WeeklyReport:
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise NotFoundError(f"Không tìm thấy báo cáo {report_id}")
    return report


@router.post("/{report_id}/extract", response_model=ReportOut)
def reextract(
    report_id: int,
    db: Session = Depends(get_db),
    provider: LlmProvider = Depends(get_llm_provider),
) -> WeeklyReport:
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise NotFoundError(f"Không tìm thấy báo cáo {report_id}")
    return reextract_report(db, report, provider)
