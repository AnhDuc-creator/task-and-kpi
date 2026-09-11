from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFoundError
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
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(kpi, field, value)
    db.commit()
    db.refresh(kpi)
    return kpi
