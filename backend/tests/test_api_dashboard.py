from datetime import date, timedelta

import pytest

TODAY = date.today()
PERIOD_START = TODAY - timedelta(days=50)
PERIOD_END = TODAY + timedelta(days=50)


@pytest.fixture
def kpi(api_client):
    employee = api_client.post(
        "/api/employees", json={"name": "Nguyen Van A", "email": "a@example.com"}
    ).json()
    return api_client.post(
        "/api/kpis",
        json={
            "name": "Hop dong ky moi",
            "target_value": 100.0,
            "unit": "hop dong",
            "owner_id": employee["id"],
            "period_start": PERIOD_START.isoformat(),
            "period_end": PERIOD_END.isoformat(),
        },
    ).json()


def test_dashboard_lists_kpi_with_zero_progress(api_client, kpi):
    body = api_client.get("/api/dashboard").json()

    assert len(body) == 1
    item = body[0]
    assert item["kpi_id"] == kpi["id"]
    assert item["actual_value"] == 0.0
    assert item["target_value"] == 100.0
    assert item["owner_name"] == "Nguyen Van A"


def test_dashboard_flags_at_risk_when_far_behind(api_client, kpi):
    item = api_client.get("/api/dashboard").json()[0]

    # đã qua ~50% kỳ, kỳ vọng ~50, thực tế 0 -> dưới 80% kỳ vọng
    assert item["at_risk"] is True
    assert item["status"] == "at_risk"


def test_dashboard_is_empty_without_kpis(api_client):
    assert api_client.get("/api/dashboard").json() == []
