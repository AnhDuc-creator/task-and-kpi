# Backend — API báo cáo tuần & KPI

## Chạy lần đầu

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Chạy server

```powershell
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Chạy test

```powershell
pytest
```

Test luôn dùng `MockProvider` và SQLite in-memory — **không gọi mạng**.

## Dùng Claude thật

Sửa `.env`:

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Mặc định là `mock`. Model mặc định là `claude-sonnet-5`.

## Thiết kế

Xem `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md`.
