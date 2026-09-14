from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Kpi
from app.schemas import KpiCreate, KpiOut, KpiUpdate
from app.services import kpi as kpi_service

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


@router.get("", response_model=list[KpiOut])
def list_kpis(db: Session = Depends(get_db)) -> list[Kpi]:
    return kpi_service.list_kpis(db)


@router.post("", response_model=KpiOut, status_code=status.HTTP_201_CREATED)
def create_kpi(payload: KpiCreate, db: Session = Depends(get_db)) -> Kpi:
    return kpi_service.create_kpi(db, **payload.model_dump())


@router.get("/{kpi_id}", response_model=KpiOut)
def get_kpi(kpi_id: int, db: Session = Depends(get_db)) -> Kpi:
    return kpi_service.get_kpi(db, kpi_id)


@router.patch("/{kpi_id}", response_model=KpiOut)
def update_kpi(
    kpi_id: int, payload: KpiUpdate, db: Session = Depends(get_db)
) -> Kpi:
    # exclude_none: PATCH là cập nhật một phần, không trường nào ở đây được
    # phép thành null. Gửi null tường minh coi như không gửi — đó là quy ước
    # định dạng trên dây, nên nó ở lại biên HTTP.
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    return kpi_service.update_kpi(db, kpi_id, changes)
