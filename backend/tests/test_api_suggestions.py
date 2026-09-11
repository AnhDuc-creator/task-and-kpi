import pytest

from app.models import KpiProgressEntry, KpiUpdateSuggestion, SuggestionStatus


@pytest.fixture
def submitted(api_client):
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
    report = api_client.post(
        "/api/reports",
        json={
            "employee_id": employee["id"],
            "week_start": "2026-03-02",
            "raw_text": "Ky them 5 hop dong ky moi.\nDa chot hop dong khach X.",
        },
    ).json()
    return {"employee": employee, "kpi": kpi, "task": task, "report": report}


def test_queue_returns_two_separate_lists(api_client, submitted):
    body = api_client.get("/api/suggestions?status=pending").json()

    assert len(body["kpi_updates"]) == 1
    assert len(body["task_completions"]) == 1
    assert body["kpi_updates"][0]["employee_name"] == "Nguyen Van A"
    assert body["kpi_updates"][0]["week_start"] == "2026-03-02"


def test_approving_kpi_suggestion(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]

    response = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={"final_kpi_id": submitted["kpi"]["id"], "final_delta": 5.0},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["final_delta"] == 5.0


def test_approving_with_edited_delta(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]

    body = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={
            "final_kpi_id": submitted["kpi"]["id"],
            "final_delta": 3.0,
            "note": "khach huy 2",
        },
    ).json()

    assert body["suggested_delta"] == 5.0
    assert body["final_delta"] == 3.0
    assert body["review_note"] == "khach huy 2"


def test_double_approval_returns_409(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]
    payload = {"final_kpi_id": submitted["kpi"]["id"], "final_delta": 5.0}
    api_client.post(f"/api/suggestions/kpi/{suggestion['id']}/approve", json=payload)

    second = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve", json=payload
    )

    assert second.status_code == 409


def test_rejecting_kpi_suggestion(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]

    response = api_client.post(f"/api/suggestions/kpi/{suggestion['id']}/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_approved_suggestion_leaves_queue(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]
    api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={"final_kpi_id": submitted["kpi"]["id"], "final_delta": 5.0},
    )

    body = api_client.get("/api/suggestions?status=pending").json()

    assert body["kpi_updates"] == []
    assert len(body["task_completions"]) == 1


def test_approving_task_suggestion_marks_task_done(api_client, submitted):
    suggestion = submitted["report"]["task_suggestions"][0]

    response = api_client.post(
        f"/api/suggestions/task/{suggestion['id']}/approve",
        json={"final_task_id": submitted["task"]["id"]},
    )

    assert response.status_code == 200
    tasks = api_client.get("/api/tasks").json()
    assert tasks[0]["status"] == "done"


def test_rejecting_task_suggestion_leaves_task_todo(api_client, submitted):
    suggestion = submitted["report"]["task_suggestions"][0]

    api_client.post(f"/api/suggestions/task/{suggestion['id']}/reject")

    tasks = api_client.get("/api/tasks").json()
    assert tasks[0]["status"] == "todo"


def test_unknown_suggestion_returns_404(api_client, submitted):
    assert api_client.post("/api/suggestions/kpi/999999/reject").status_code == 404


def test_approving_can_reassign_to_a_different_kpi(api_client, db_session, submitted):
    """`final_kpi_id` là nguồn sự thật, không phải KPI mà LLM đoán.

    Đây cũng chính là cơ chế quản lý dùng để gán KPI cho một đề xuất mà LLM
    trả về `kpi_id = null`: sổ cái phải ghi vào KPI quản lý chọn.
    """
    other = api_client.post(
        "/api/kpis",
        json={
            "name": "Doanh thu",
            "target_value": 1000.0,
            "unit": "trieu",
            "owner_id": submitted["employee"]["id"],
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    ).json()
    suggestion = submitted["report"]["kpi_suggestions"][0]
    assert suggestion["suggested_kpi_id"] == submitted["kpi"]["id"]

    body = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={"final_kpi_id": other["id"], "final_delta": 5.0},
    ).json()

    assert body["suggested_kpi_id"] == submitted["kpi"]["id"]  # bản gốc còn nguyên
    assert body["final_kpi_id"] == other["id"]

    entry = db_session.query(KpiProgressEntry).one()
    assert entry.kpi_id == other["id"]


def _post_raw_json(api_client, url, raw_body):
    """Gửi thân JSON thô: cần để đưa `1e400`/`NaN` qua HTTP, vì `json=` của
    client sẽ tự chặn các giá trị không hữu hạn trước khi gửi đi."""
    return api_client.post(
        url, content=raw_body.encode(), headers={"Content-Type": "application/json"}
    )


def test_approving_with_infinite_delta_is_rejected(api_client, db_session, submitted):
    """`1e400` là JSON hợp lệ nhưng Python parse ra `inf` — đây chính là repro
    của lỗi nghiêm trọng: sổ cái phải còn trống và suggestion còn `pending`."""
    suggestion = submitted["report"]["kpi_suggestions"][0]

    response = _post_raw_json(
        api_client,
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        '{"final_kpi_id": %d, "final_delta": 1e400}' % submitted["kpi"]["id"],
    )

    assert response.status_code == 422
    assert db_session.query(KpiProgressEntry).count() == 0
    db_session.expire_all()
    stored = db_session.get(KpiUpdateSuggestion, suggestion["id"])
    assert stored.status is SuggestionStatus.PENDING


def test_approving_with_nan_delta_is_rejected(api_client, db_session, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]

    response = _post_raw_json(
        api_client,
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        '{"final_kpi_id": %d, "final_delta": NaN}' % submitted["kpi"]["id"],
    )

    assert response.status_code == 422
    assert db_session.query(KpiProgressEntry).count() == 0
    db_session.expire_all()
    stored = db_session.get(KpiUpdateSuggestion, suggestion["id"])
    assert stored.status is SuggestionStatus.PENDING
