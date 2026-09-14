"""Nghiệp vụ Task. Router chỉ dịch HTTP; mọi quyết định nghiệp vụ và ranh giới
giao dịch nằm ở đây.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Employee, Kpi, Task


def _load_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Không tìm thấy task {task_id}")
    return task


def list_tasks(db: Session) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.id)).all())


def create_task(db: Session, *, title: str, kpi_id: int, assignee_id: int) -> Task:
    if db.get(Kpi, kpi_id) is None:
        raise NotFoundError(f"Không tìm thấy KPI {kpi_id}")
    if db.get(Employee, assignee_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {assignee_id}")

    task = Task(title=title, kpi_id=kpi_id, assignee_id=assignee_id)
    try:
        db.add(task)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(task)
    return task


def update_task(db: Session, task_id: int, changes: dict[str, Any]) -> Task:
    task = _load_task(db, task_id)

    for field, value in changes.items():
        setattr(task, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(task)
    return task
