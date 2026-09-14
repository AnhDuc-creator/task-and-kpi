"""Nghiệp vụ Task. Router chỉ dịch HTTP; mọi quyết định nghiệp vụ và ranh giới
giao dịch nằm ở đây.
"""

from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Employee, Kpi, Task, TaskStatus


class TaskChanges(TypedDict, total=False):
    """Các trường được phép sửa qua update_task — khớp 1-1 với TaskUpdate
    trong app/schemas.py. Chỉ để tài liệu hoá: dự án không chạy mypy nên
    TypedDict không tự chặn được key lạ, xem whitelist runtime bên dưới.
    """

    title: str
    status: TaskStatus


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


def update_task(db: Session, task_id: int, changes: TaskChanges) -> Task:
    task = _load_task(db, task_id)

    # Key lạ là lỗi lập trình của nơi gọi (router/test), không phải dữ liệu
    # người dùng nhập sai, nên ném ValueError chứ không phải lỗi nghiệp vụ
    # trong app.errors — nó không được phép lọt ra thành một mã HTTP 4xx.
    unknown = set(changes) - TaskChanges.__optional_keys__
    if unknown:
        raise ValueError(
            f"update_task nhận trường không được phép: {sorted(unknown)}"
        )

    for field, value in changes.items():
        setattr(task, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(task)
    return task
