"""Dashboard. `current_value` luôn được tính từ sổ cái, không có cột lưu sẵn."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Kpi, KpiProgressEntry
from app.rules import KpiEvaluation, evaluate_kpi


@dataclass(frozen=True)
class DashboardItem:
    kpi_id: int
    kpi_name: str
    unit: str
    owner_name: str
    period_start: date
    period_end: date
    evaluation: KpiEvaluation


def current_values(db: Session) -> dict[int, float]:
    """Tổng delta đã duyệt của từng KPI. KPI chưa có dòng nào sẽ không xuất hiện."""
    rows = db.execute(
        select(KpiProgressEntry.kpi_id, func.sum(KpiProgressEntry.delta_value)).group_by(
            KpiProgressEntry.kpi_id
        )
    ).all()
    return {kpi_id: float(total) for kpi_id, total in rows}


def build_dashboard(db: Session, today: date) -> list[DashboardItem]:
    totals = current_values(db)
    kpis = db.scalars(select(Kpi).order_by(Kpi.id)).all()

    return [
        DashboardItem(
            kpi_id=kpi.id,
            kpi_name=kpi.name,
            unit=kpi.unit,
            owner_name=kpi.owner.name,
            period_start=kpi.period_start,
            period_end=kpi.period_end,
            evaluation=evaluate_kpi(
                target_value=kpi.target_value,
                actual_value=totals.get(kpi.id, 0.0),
                period_start=kpi.period_start,
                period_end=kpi.period_end,
                today=today,
            ),
        )
        for kpi in kpis
    ]
