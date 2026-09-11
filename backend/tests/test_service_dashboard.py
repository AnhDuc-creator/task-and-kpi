from datetime import date

import pytest

from app.models import Employee, Kpi, KpiProgressEntry
from app.rules import KpiStatus
from app.services.dashboard import build_dashboard, current_values

START = date(2026, 1, 1)
END = date(2026, 1, 11)
MIDWAY = date(2026, 1, 6)


@pytest.fixture
def kpi(db_session):
    employee = Employee(name="Nguyen Van A", email="a@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=employee.id,
        period_start=START,
        period_end=END,
    )
    db_session.add(kpi)
    db_session.commit()
    return kpi


def test_kpi_without_entries_has_zero_actual(db_session, kpi):
    assert current_values(db_session) == {}

    items = build_dashboard(db_session, today=MIDWAY)
    assert items[0].evaluation.actual_value == 0.0


def test_current_value_sums_entries(db_session, kpi):
    db_session.add_all(
        [
            KpiProgressEntry(kpi_id=kpi.id, delta_value=10.0, effective_date=START),
            KpiProgressEntry(kpi_id=kpi.id, delta_value=5.5, effective_date=START),
        ]
    )
    db_session.commit()

    assert current_values(db_session) == {kpi.id: 15.5}


def test_dashboard_flags_at_risk(db_session, kpi):
    db_session.add(
        KpiProgressEntry(kpi_id=kpi.id, delta_value=10.0, effective_date=START)
    )
    db_session.commit()

    item = build_dashboard(db_session, today=MIDWAY)[0]

    assert item.evaluation.expected_value == 50.0
    assert item.evaluation.status is KpiStatus.AT_RISK


def test_dashboard_clears_warning_once_enough_progress(db_session, kpi):
    db_session.add(
        KpiProgressEntry(kpi_id=kpi.id, delta_value=60.0, effective_date=START)
    )
    db_session.commit()

    item = build_dashboard(db_session, today=MIDWAY)[0]

    assert item.evaluation.at_risk is False
    assert item.evaluation.status is KpiStatus.ON_TRACK


def test_dashboard_includes_metadata(db_session, kpi):
    item = build_dashboard(db_session, today=MIDWAY)[0]

    assert item.kpi_id == kpi.id
    assert item.kpi_name == "Hop dong ky moi"
    assert item.unit == "hop dong"
    assert item.owner_name == "Nguyen Van A"
    assert item.period_start == START


def test_entries_of_other_kpi_do_not_leak(db_session, kpi):
    other = Kpi(
        name="Doanh thu",
        target_value=1000.0,
        unit="trieu",
        owner_id=kpi.owner_id,
        period_start=START,
        period_end=END,
    )
    db_session.add(other)
    db_session.flush()
    db_session.add_all(
        [
            KpiProgressEntry(kpi_id=kpi.id, delta_value=10.0, effective_date=START),
            KpiProgressEntry(kpi_id=other.id, delta_value=999.0, effective_date=START),
        ]
    )
    db_session.commit()

    values = current_values(db_session)
    assert values[kpi.id] == 10.0
    assert values[other.id] == 999.0
