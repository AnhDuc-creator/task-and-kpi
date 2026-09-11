from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import DashboardItemOut
from app.services.dashboard import build_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=list[DashboardItemOut])
def get_dashboard(db: Session = Depends(get_db)) -> list[DashboardItemOut]:
    # "Hôm nay" chỉ được đọc ở biên HTTP; service và rules luôn nhận nó qua tham số.
    items = build_dashboard(db, today=date.today())
    return [
        DashboardItemOut(
            kpi_id=item.kpi_id,
            kpi_name=item.kpi_name,
            unit=item.unit,
            owner_name=item.owner_name,
            period_start=item.period_start,
            period_end=item.period_end,
            actual_value=item.evaluation.actual_value,
            target_value=item.evaluation.target_value,
            expected_value=item.evaluation.expected_value,
            percent_complete=item.evaluation.percent_complete,
            status=item.evaluation.status.value,
            at_risk=item.evaluation.at_risk,
        )
        for item in items
    ]
