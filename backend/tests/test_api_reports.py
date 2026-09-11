import pytest

from app.models import KpiUpdateSuggestion


@pytest.fixture
def seeded(api_client):
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
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    ).json()
    task = api_client.post(
        "/api/tasks",
        json={
            "title": "Chot hop dong khach X",
            "kpi_id": kpi["id"],
            "assignee_id": employee["id"],
        },
    ).json()
    return {"employee": employee, "kpi": kpi, "task": task}


def submit(api_client, employee_id, text="Ky them 5 hop dong ky moi."):
    return api_client.post(
        "/api/reports",
        json={"employee_id": employee_id, "week_start": "2026-03-02", "raw_text": text},
    )


def test_submitting_report_returns_suggestions(api_client, seeded):
    response = submit(api_client, seeded["employee"]["id"])

    assert response.status_code == 201
    body = response.json()
    assert body["extraction_status"] == "extracted"
    assert body["provider_name"] == "mock"
    assert len(body["kpi_suggestions"]) == 1
    assert body["kpi_suggestions"][0]["suggested_delta"] == 5.0
    assert body["kpi_suggestions"][0]["status"] == "pending"


def test_duplicate_submission_returns_409(api_client, seeded):
    submit(api_client, seeded["employee"]["id"])

    second = submit(api_client, seeded["employee"]["id"], text="lan hai")

    assert second.status_code == 409
    assert len(api_client.get("/api/reports").json()) == 1


def test_get_report_by_id(api_client, seeded):
    created = submit(api_client, seeded["employee"]["id"]).json()

    fetched = api_client.get(f"/api/reports/{created['id']}").json()

    assert fetched["id"] == created["id"]
    assert fetched["raw_text"] == "Ky them 5 hop dong ky moi."


def test_get_unknown_report_returns_404(api_client):
    assert api_client.get("/api/reports/999999").status_code == 404


def test_reextract_replaces_pending_suggestions(api_client, db_session, seeded):
    """Đánh dấu dòng cũ rồi kiểm dòng còn lại không mang dấu đó.

    Không so sánh id: SQLite cấp lại khoá chính khi bảng bị xoá sạch, nên id
    trùng nhau là bình thường và không chứng minh điều gì. `api_client` dùng
    chung session với `db_session` nên đánh dấu được trực tiếp.
    """
    created = submit(api_client, seeded["employee"]["id"]).json()
    old = db_session.get(KpiUpdateSuggestion, created["kpi_suggestions"][0]["id"])
    old.evidence = "DAU VET CU"
    db_session.commit()

    response = api_client.post(f"/api/reports/{created['id']}/extract")

    assert response.status_code == 200
    suggestions = response.json()["kpi_suggestions"]
    assert len(suggestions) == 1
    assert suggestions[0]["evidence"] != "DAU VET CU"


def test_failed_extraction_is_reported(api_client, seeded):
    """Nhân viên không có KPI/Task nào -> mock không trích được gì, nhưng vẫn
    là một lần trích xuất thành công với danh sách rỗng."""
    other = api_client.post(
        "/api/employees", json={"name": "Tran Thi B", "email": "b@example.com"}
    ).json()

    body = submit(api_client, other["id"], text="Tuan nay hop giao ban.").json()

    assert body["extraction_status"] == "extracted"
    assert body["kpi_suggestions"] == []
    assert body["blockers"] == []
