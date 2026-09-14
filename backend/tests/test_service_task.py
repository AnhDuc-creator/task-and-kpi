from datetime import date

import pytest

from app.errors import NotFoundError
from app.models import TaskStatus
from app.services import employee as employee_service
from app.services import kpi as kpi_service
from app.services import task as task_service


def make_fixtures(db_session):
    owner = employee_service.create_employee(
        db_session, name="Chu viec", email="owner@example.com"
    )
    kpi = kpi_service.create_kpi(
        db_session,
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=owner.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    return owner, kpi


def test_create_task_defaults_to_todo(db_session):
    owner, kpi = make_fixtures(db_session)

    created = task_service.create_task(
        db_session, title="Chot hop dong khach X", kpi_id=kpi.id, assignee_id=owner.id
    )

    assert created.id is not None
    assert created.status is TaskStatus.TODO


def test_create_task_with_unknown_kpi_raises_not_found(db_session):
    owner, _ = make_fixtures(db_session)

    with pytest.raises(NotFoundError):
        task_service.create_task(
            db_session, title="x", kpi_id=999999, assignee_id=owner.id
        )


def test_create_task_with_unknown_assignee_raises_not_found(db_session):
    _, kpi = make_fixtures(db_session)

    with pytest.raises(NotFoundError):
        task_service.create_task(
            db_session, title="x", kpi_id=kpi.id, assignee_id=999999
        )


def test_update_task_applies_changes(db_session):
    owner, kpi = make_fixtures(db_session)
    task = task_service.create_task(
        db_session, title="Viec A", kpi_id=kpi.id, assignee_id=owner.id
    )

    updated = task_service.update_task(
        db_session, task.id, {"status": TaskStatus.DOING}
    )

    assert updated.status is TaskStatus.DOING


def test_update_unknown_task_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        task_service.update_task(db_session, 999999, {"title": "x"})


def test_list_tasks_is_ordered_by_id(db_session):
    owner, kpi = make_fixtures(db_session)
    first = task_service.create_task(
        db_session, title="Viec 1", kpi_id=kpi.id, assignee_id=owner.id
    )
    second = task_service.create_task(
        db_session, title="Viec 2", kpi_id=kpi.id, assignee_id=owner.id
    )

    assert [row.id for row in task_service.list_tasks(db_session)] == [
        first.id,
        second.id,
    ]


def test_update_task_rejects_unknown_field_and_keeps_stored_row(db_session):
    """Key lạ (vd. kpi_id, id) là lỗi lập trình của nơi gọi, không phải
    payload người dùng — router chỉ bao giờ gửi các trường TaskUpdate cho
    phép, nên guard này chỉ có thể bị chạm bởi service/test gọi trực tiếp."""
    owner, kpi = make_fixtures(db_session)
    task = task_service.create_task(
        db_session, title="Viec A", kpi_id=kpi.id, assignee_id=owner.id
    )

    with pytest.raises(ValueError):
        task_service.update_task(db_session, task.id, {"kpi_id": 999999})

    stored = task_service.list_tasks(db_session)[0]
    assert stored.kpi_id == kpi.id
    assert stored.title == "Viec A"
