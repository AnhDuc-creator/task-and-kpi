from datetime import date

import pytest

from app.errors import InvalidInputError, NotFoundError
from app.services import employee as employee_service
from app.services import kpi as kpi_service


def make_owner(db_session, email="owner@example.com"):
    return employee_service.create_employee(db_session, name="Chu KPI", email=email)


def make_kpi(db_session, owner_id, **overrides):
    fields = {
        "name": "Hop dong ky moi",
        "target_value": 100.0,
        "unit": "hop dong",
        "owner_id": owner_id,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 12, 31),
    }
    fields.update(overrides)
    return kpi_service.create_kpi(db_session, **fields)


def test_create_kpi_persists_row(db_session):
    owner = make_owner(db_session)
    created = make_kpi(db_session, owner.id)

    assert created.id is not None
    assert kpi_service.get_kpi(db_session, created.id).target_value == 100.0


def test_create_kpi_with_unknown_owner_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        make_kpi(db_session, 999999)


def test_get_unknown_kpi_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        kpi_service.get_kpi(db_session, 999999)


def test_update_kpi_applies_changes(db_session):
    owner = make_owner(db_session)
    kpi = make_kpi(db_session, owner.id)

    updated = kpi_service.update_kpi(db_session, kpi.id, {"target_value": 150.0})

    assert updated.target_value == 150.0


def test_update_kpi_rejects_inverted_period_and_keeps_stored_value(db_session):
    """PATCH chỉ đổi một mốc vẫn phải bị chặn nếu tạo ra kỳ ngược, và giá trị
    đang lưu phải nguyên vẹn sau khi service rollback."""
    owner = make_owner(db_session)
    kpi = make_kpi(db_session, owner.id)

    with pytest.raises(InvalidInputError):
        kpi_service.update_kpi(db_session, kpi.id, {"period_end": date(2025, 1, 1)})

    assert kpi_service.get_kpi(db_session, kpi.id).period_end == date(2026, 12, 31)


def test_update_unknown_kpi_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        kpi_service.update_kpi(db_session, 999999, {"target_value": 5.0})


def test_list_kpis_is_ordered_by_id(db_session):
    owner = make_owner(db_session)
    first = make_kpi(db_session, owner.id, name="KPI 1")
    second = make_kpi(db_session, owner.id, name="KPI 2")

    assert [row.id for row in kpi_service.list_kpis(db_session)] == [
        first.id,
        second.id,
    ]


def test_update_kpi_rejects_unknown_field_and_keeps_stored_row(db_session):
    """Key lạ (vd. owner_id, id) là lỗi lập trình của nơi gọi, không phải
    payload người dùng — router chỉ bao giờ gửi các trường KpiUpdate cho phép,
    nên guard này chỉ có thể bị chạm bởi service/test gọi trực tiếp."""
    owner = make_owner(db_session)
    kpi = make_kpi(db_session, owner.id)

    with pytest.raises(ValueError):
        kpi_service.update_kpi(db_session, kpi.id, {"owner_id": 999999})

    stored = kpi_service.get_kpi(db_session, kpi.id)
    assert stored.owner_id == owner.id
    assert stored.target_value == 100.0
