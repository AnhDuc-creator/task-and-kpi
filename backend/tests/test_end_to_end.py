from datetime import date, timedelta

TODAY = date.today()
PERIOD_START = TODAY - timedelta(days=50)
PERIOD_END = TODAY + timedelta(days=50)


def test_full_cycle_from_kpi_to_dashboard(api_client):
    """Tạo KPI -> nộp báo cáo -> duyệt -> dashboard đổi số và tắt cảnh báo."""
    employee = api_client.post(
        "/api/employees", json={"name": "Nguyen Van A", "email": "a@example.com"}
    ).json()
    kpi = api_client.post(
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

    before = api_client.get("/api/dashboard").json()[0]
    assert before["actual_value"] == 0.0
    assert before["at_risk"] is True

    report = api_client.post(
        "/api/reports",
        json={
            "employee_id": employee["id"],
            "week_start": "2026-03-02",
            "raw_text": "Tuan nay ky them 60 hop dong ky moi.",
        },
    ).json()
    assert report["extraction_status"] == "extracted"
    suggestion = report["kpi_suggestions"][0]
    assert suggestion["suggested_delta"] == 60.0

    queue = api_client.get("/api/suggestions?status=pending").json()
    assert len(queue["kpi_updates"]) == 1

    approved = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={"final_kpi_id": kpi["id"], "final_delta": 60.0},
    )
    assert approved.status_code == 200

    after = api_client.get("/api/dashboard").json()[0]
    assert after["actual_value"] == 60.0
    assert after["at_risk"] is False
    assert after["status"] == "on_track"

    assert api_client.get("/api/suggestions?status=pending").json()["kpi_updates"] == []
