"""Nghiệp vụ KPI. Router chỉ dịch HTTP; mọi quyết định nghiệp vụ và ranh giới
giao dịch nằm ở đây.
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInputError, NotFoundError
from app.models import Employee, Kpi


def list_kpis(db: Session) -> list[Kpi]:
    return list(db.scalars(select(Kpi).order_by(Kpi.id)).all())


def get_kpi(db: Session, kpi_id: int) -> Kpi:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise NotFoundError(f"Không tìm thấy KPI {kpi_id}")
    return kpi


def create_kpi(
    db: Session,
    *,
    name: str,
    target_value: float,
    unit: str,
    owner_id: int,
    period_start: date,
    period_end: date,
) -> Kpi:
    if db.get(Employee, owner_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {owner_id}")

    kpi = Kpi(
        name=name,
        target_value=target_value,
        unit=unit,
        owner_id=owner_id,
        period_start=period_start,
        period_end=period_end,
    )
    try:
        db.add(kpi)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(kpi)
    return kpi


def update_kpi(db: Session, kpi_id: int, changes: dict[str, Any]) -> Kpi:
    kpi = get_kpi(db, kpi_id)

    for field, value in changes.items():
        setattr(kpi, field, value)

    # Kiểm sau khi đã trộn với giá trị đang lưu: PATCH chỉ đổi một trong hai
    # mốc thời gian vẫn có thể tạo ra kỳ ngược. Kỳ ngược khiến
    # compute_elapsed_ratio coi như kỳ dài 0 ngày và trả 1.0, làm KPI bị
    # cảnh báo "có nguy cơ" oan. rollback() vứt bỏ các setattr ở trên.
    if kpi.period_end < kpi.period_start:
        db.rollback()
        raise InvalidInputError("period_end phải không nhỏ hơn period_start")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(kpi)
    return kpi
