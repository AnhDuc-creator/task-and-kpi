from datetime import date

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ConflictError
from app.llm.base import (
    ExtractionError,
    ExtractionRequest,
    KpiCatalogItem,
    LlmProvider,
    TaskCatalogItem,
    validate_extraction_result,
)
from app.models import (
    Blocker,
    ExtractionStatus,
    Kpi,
    KpiUpdateSuggestion,
    SuggestionStatus,
    Task,
    TaskCompletionSuggestion,
    TaskStatus,
    WeeklyReport,
)


def build_extraction_request(db: Session, report: WeeklyReport) -> ExtractionRequest:
    """Catalog gồm KPI do nhân viên phụ trách và Task của họ chưa hoàn thành."""
    kpis = db.scalars(select(Kpi).where(Kpi.owner_id == report.employee_id)).all()
    tasks = db.scalars(
        select(Task).where(
            Task.assignee_id == report.employee_id, Task.status != TaskStatus.DONE
        )
    ).all()

    return ExtractionRequest(
        report_text=report.raw_text,
        kpi_catalog=[
            KpiCatalogItem(
                id=kpi.id, name=kpi.name, unit=kpi.unit, target_value=kpi.target_value
            )
            for kpi in kpis
        ],
        task_catalog=[TaskCatalogItem(id=task.id, title=task.title) for task in tasks],
    )


def run_extraction(
    db: Session, report: WeeklyReport, provider: LlmProvider
) -> WeeklyReport:
    """Gọi provider và ghi kết quả. Thất bại → failed, không tạo suggestion nào.

    `validate_extraction_result` được gọi ở đây, sau MỌI provider, nên không
    provider nào tự miễn trừ được ràng buộc catalog và delta hữu hạn.
    `ValidationError` cũng được bắt: một provider ném lỗi Pydantic thì báo cáo
    phải thành `failed`, chứ không được làm sập request.
    """
    request = build_extraction_request(db, report)
    report.provider_name = provider.name

    try:
        result = provider.extract(request)
        validate_extraction_result(result, request)
    except (ExtractionError, ValidationError) as exc:
        report.extraction_status = ExtractionStatus.FAILED
        report.extraction_error = str(exc)
        db.commit()
        return report

    for update in result.kpi_updates:
        db.add(
            KpiUpdateSuggestion(
                report_id=report.id,
                suggested_kpi_id=update.kpi_id,
                suggested_delta=update.delta_value,
                evidence=update.evidence,
            )
        )
    for task_done in result.tasks_done:
        db.add(
            TaskCompletionSuggestion(
                report_id=report.id,
                suggested_task_id=task_done.task_id,
                raw_text=task_done.description,
            )
        )
    for blocker in result.blockers:
        db.add(
            Blocker(
                report_id=report.id,
                description=blocker.description,
                related_kpi_id=blocker.related_kpi_id,
            )
        )

    report.extraction_status = ExtractionStatus.EXTRACTED
    report.extraction_error = None
    report.raw_llm_response = result.model_dump_json()
    db.commit()
    db.refresh(report)
    return report


def submit_report(
    db: Session,
    *,
    employee_id: int,
    week_start: date,
    raw_text: str,
    provider: LlmProvider,
) -> WeeklyReport:
    existing = db.scalar(
        select(WeeklyReport).where(
            WeeklyReport.employee_id == employee_id,
            WeeklyReport.week_start == week_start,
        )
    )
    if existing is not None:
        raise ConflictError("Nhân viên này đã nộp báo cáo cho tuần đó")

    report = WeeklyReport(
        employee_id=employee_id, week_start=week_start, raw_text=raw_text
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return run_extraction(db, report, provider)


def _has_approved_suggestion(db: Session, report_id: int) -> bool:
    """Quét CẢ HAI bảng suggestion — một dòng approved ở bất kỳ bảng nào cũng tính."""
    approved_kpi = db.scalar(
        select(KpiUpdateSuggestion.id).where(
            KpiUpdateSuggestion.report_id == report_id,
            KpiUpdateSuggestion.status == SuggestionStatus.APPROVED,
        )
    )
    if approved_kpi is not None:
        return True
    approved_task = db.scalar(
        select(TaskCompletionSuggestion.id).where(
            TaskCompletionSuggestion.report_id == report_id,
            TaskCompletionSuggestion.status == SuggestionStatus.APPROVED,
        )
    )
    return approved_task is not None


def reextract_report(
    db: Session, report: WeeklyReport, provider: LlmProvider
) -> WeeklyReport:
    """Chạy lại trích xuất cho một báo cáo.

    Cho phép khi báo cáo đang `failed`, HOẶC khi chưa có suggestion nào được
    duyệt. Một dòng đã duyệt là khoá báo cáo lại, vì số liệu đã vào sổ cái.
    """
    if (
        report.extraction_status is not ExtractionStatus.FAILED
        and _has_approved_suggestion(db, report.id)
    ):
        raise ConflictError(
            "Báo cáo đã có đề xuất được duyệt nên không thể trích xuất lại"
        )

    for suggestion in list(report.kpi_suggestions):
        if suggestion.status is SuggestionStatus.PENDING:
            db.delete(suggestion)
    for suggestion in list(report.task_suggestions):
        if suggestion.status is SuggestionStatus.PENDING:
            db.delete(suggestion)
    for blocker in list(report.blockers):
        db.delete(blocker)

    report.extraction_status = ExtractionStatus.PENDING
    report.extraction_error = None
    report.raw_llm_response = None
    db.commit()
    db.refresh(report)

    return run_extraction(db, report, provider)
