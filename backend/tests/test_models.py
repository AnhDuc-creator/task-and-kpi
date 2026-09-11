from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Employee,
    ExtractionStatus,
    Kpi,
    KpiProgressEntry,
    Task,
    TaskStatus,
    WeeklyReport,
)


def test_can_persist_full_object_graph(db_session):
    employee = Employee(name="Nguyen Van A", email="a@example.com")
    db_session.add(employee)
    db_session.flush()

    kpi = Kpi(
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()

    task = Task(
        title="Chot hop dong voi khach X",
        kpi_id=kpi.id,
        assignee_id=employee.id,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    db_session.commit()

    assert task.id is not None
    assert task.status is TaskStatus.TODO


def test_report_defaults_to_pending_extraction(db_session):
    employee = Employee(name="B", email="b@example.com")
    db_session.add(employee)
    db_session.flush()

    report = WeeklyReport(
        employee_id=employee.id,
        week_start=date(2026, 3, 2),
        raw_text="Tuan nay lam viec X",
    )
    db_session.add(report)
    db_session.commit()

    assert report.extraction_status is ExtractionStatus.PENDING
    assert report.submitted_at is not None


def test_duplicate_employee_week_is_rejected(db_session):
    employee = Employee(name="C", email="c@example.com")
    db_session.add(employee)
    db_session.flush()

    db_session.add(
        WeeklyReport(
            employee_id=employee.id, week_start=date(2026, 3, 2), raw_text="lan 1"
        )
    )
    db_session.commit()

    db_session.add(
        WeeklyReport(
            employee_id=employee.id, week_start=date(2026, 3, 2), raw_text="lan 2"
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_week_different_employee_is_allowed(db_session):
    first = Employee(name="D", email="d@example.com")
    second = Employee(name="E", email="e@example.com")
    db_session.add_all([first, second])
    db_session.flush()

    db_session.add_all(
        [
            WeeklyReport(
                employee_id=first.id, week_start=date(2026, 3, 2), raw_text="x"
            ),
            WeeklyReport(
                employee_id=second.id, week_start=date(2026, 3, 2), raw_text="y"
            ),
        ]
    )
    db_session.commit()

    assert db_session.query(WeeklyReport).count() == 2


def test_enum_columns_store_lowercase_values(db_session):
    """DB phải chứa `todo`/`pending`, không phải tên hằng `TODO`/`PENDING`.

    Mặc định SQLAlchemy lưu tên hằng; spec quy định từ vựng chữ thường. Test
    đọc thẳng bằng SQL thô để không bị ORM dịch ngược che mất.
    """
    from sqlalchemy import text

    employee = Employee(name="G", email="g@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Doanh thu",
        target_value=10.0,
        unit="trieu",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()
    db_session.add(
        Task(
            title="Viec A",
            kpi_id=kpi.id,
            assignee_id=employee.id,
            status=TaskStatus.TODO,
        )
    )
    db_session.add(
        WeeklyReport(
            employee_id=employee.id, week_start=date(2026, 3, 2), raw_text="x"
        )
    )
    db_session.commit()

    assert db_session.execute(text("SELECT status FROM tasks")).scalar() == "todo"
    assert (
        db_session.execute(text("SELECT extraction_status FROM weekly_reports")).scalar()
        == "pending"
    )


def test_progress_entries_accumulate(db_session):
    employee = Employee(name="F", email="f@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Doanh thu",
        target_value=1000.0,
        unit="trieu",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()

    db_session.add_all(
        [
            KpiProgressEntry(
                kpi_id=kpi.id, delta_value=10.0, effective_date=date(2026, 2, 2)
            ),
            KpiProgressEntry(
                kpi_id=kpi.id, delta_value=5.5, effective_date=date(2026, 2, 9)
            ),
        ]
    )
    db_session.commit()

    total = sum(entry.delta_value for entry in kpi.progress_entries)
    assert total == 15.5
