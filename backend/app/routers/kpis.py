from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import InvalidInputError, NotFoundError
from app.models import Employee, Kpi
from app.schemas import KpiCreate, KpiOut, KpiUpdate

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


@router.get("", response_model=list[KpiOut])
def list_kpis(db: Session = Depends(get_db)) -> list[Kpi]:
    return list(db.scalars(select(Kpi).order_by(Kpi.id)).all())


@router.post("", response_model=KpiOut, status_code=status.HTTP_201_CREATED)
def create_kpi(payload: KpiCreate, db: Session = Depends(get_db)) -> Kpi:
    if db.get(Employee, payload.owner_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {payload.owner_id}")
    kpi = Kpi(**payload.model_dump())
    db.add(kpi)
    db.commit()
    db.refresh(kpi)
    return kpi


@router.get("/{kpi_id}", response_model=KpiOut)
def get_kpi(kpi_id: int, db: Session = Depends(get_db)) -> Kpi:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise NotFoundError(f"Không tìm thấy KPI {kpi_id}")
    return kpi


@router.patch("/{kpi_id}", response_model=KpiOut)
def update_kpi(
    kpi_id: int, payload: KpiUpdate, db: Session = Depends(get_db)
) -> Kpi:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise NotFoundError(f"Không tìm thấy KPI {kpi_id}")

    # exclude_none: PATCH là cập nhật một phần, không trường nào ở đây được
    # phép thành null. Gửi null tường minh coi như không gửi.
    for field, value in payload.model_dump(
        exclude_unset=True, exclude_none=True
    ).items():
        setattr(kpi, field, value)

    # Kiểm sau khi đã trộn với giá trị đang lưu: PATCH chỉ đổi một trong hai
    # mốc thời gian vẫn có thể tạo ra kỳ ngược. Kỳ ngược khiến
    # compute_elapsed_ratio coi như kỳ dài 0 ngày và trả 1.0, làm KPI bị
    # cảnh báo "có nguy cơ" oan.
    if kpi.period_end < kpi.period_start:
        db.rollback()
        raise InvalidInputError("period_end phải không nhỏ hơn period_start")

    db.commit()
    db.refresh(kpi)
    return kpi
