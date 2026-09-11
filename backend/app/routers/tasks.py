from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFoundError
from app.models import Employee, Kpi, Task
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.id)).all())


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    if db.get(Kpi, payload.kpi_id) is None:
        raise NotFoundError(f"Không tìm thấy KPI {payload.kpi_id}")
    if db.get(Employee, payload.assignee_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {payload.assignee_id}")
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)
) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Không tìm thấy task {task_id}")
    for field, value in payload.model_dump(
        exclude_unset=True, exclude_none=True
    ).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task
