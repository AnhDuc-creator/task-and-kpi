def create_employee(client, email="a@example.com"):
    response = client.post(
        "/api/employees", json={"name": "Nguyen Van A", "email": email}
    )
    assert response.status_code == 201
    return response.json()


def create_kpi(client, owner_id):
    response = client.post(
        "/api/kpis",
        json={
            "name": "Hop dong ky moi",
            "target_value": 100.0,
            "unit": "hop dong",
            "owner_id": owner_id,
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_list_employees(api_client):
    created = create_employee(api_client)
    assert created["id"] > 0

    listed = api_client.get("/api/employees").json()
    assert [item["email"] for item in listed] == ["a@example.com"]


def test_create_and_get_kpi(api_client):
    employee = create_employee(api_client)
    kpi = create_kpi(api_client, employee["id"])

    fetched = api_client.get(f"/api/kpis/{kpi['id']}").json()
    assert fetched["name"] == "Hop dong ky moi"
    assert fetched["target_value"] == 100.0


def test_kpi_response_has_no_current_value_field(api_client):
    employee = create_employee(api_client)
    kpi = create_kpi(api_client, employee["id"])
    assert "current_value" not in kpi


def test_get_unknown_kpi_returns_404(api_client):
    assert api_client.get("/api/kpis/999999").status_code == 404


def test_patch_kpi_target(api_client):
    employee = create_employee(api_client)
    kpi = create_kpi(api_client, employee["id"])

    response = api_client.patch(f"/api/kpis/{kpi['id']}", json={"target_value": 150.0})

    assert response.status_code == 200
    assert response.json()["target_value"] == 150.0


def test_non_positive_target_is_rejected(api_client):
    employee = create_employee(api_client)
    response = api_client.post(
        "/api/kpis",
        json={
            "name": "Sai",
            "target_value": 0,
            "unit": "cai",
            "owner_id": employee["id"],
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    assert response.status_code == 422


def test_period_end_before_start_is_rejected(api_client):
    employee = create_employee(api_client)
    response = api_client.post(
        "/api/kpis",
        json={
            "name": "Sai",
            "target_value": 10,
            "unit": "cai",
            "owner_id": employee["id"],
            "period_start": "2026-12-31",
            "period_end": "2026-01-01",
        },
    )
    assert response.status_code == 422


def test_create_and_patch_task(api_client):
    employee = create_employee(api_client)
    kpi = create_kpi(api_client, employee["id"])

    created = api_client.post(
        "/api/tasks",
        json={
            "title": "Chot hop dong khach X",
            "kpi_id": kpi["id"],
            "assignee_id": employee["id"],
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "todo"

    patched = api_client.patch(
        f"/api/tasks/{created.json()['id']}", json={"status": "doing"}
    )
    assert patched.json()["status"] == "doing"


def test_task_with_unknown_kpi_returns_404(api_client):
    employee = create_employee(api_client)
    response = api_client.post(
        "/api/tasks",
        json={"title": "x", "kpi_id": 999999, "assignee_id": employee["id"]},
    )
    assert response.status_code == 404
