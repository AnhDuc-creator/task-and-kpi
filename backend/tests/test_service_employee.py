import pytest

from app.errors import ConflictError
from app.models import Employee
from app.services import employee as employee_service


def test_create_employee_persists_and_returns_row(db_session):
    created = employee_service.create_employee(
        db_session, name="Nguyen Van A", email="a@example.com"
    )

    assert created.id is not None
    assert db_session.get(Employee, created.id).email == "a@example.com"


def test_create_employee_with_duplicate_email_raises_conflict(db_session):
    employee_service.create_employee(
        db_session, name="Nguoi thu nhat", email="a@example.com"
    )

    with pytest.raises(ConflictError):
        employee_service.create_employee(
            db_session, name="Nguoi thu hai", email="a@example.com"
        )

    assert len(employee_service.list_employees(db_session)) == 1


def test_list_employees_is_ordered_by_id(db_session):
    first = employee_service.create_employee(db_session, name="A", email="a@example.com")
    second = employee_service.create_employee(db_session, name="B", email="b@example.com")

    assert [row.id for row in employee_service.list_employees(db_session)] == [
        first.id,
        second.id,
    ]
