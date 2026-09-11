# task-and-kpi — báo cáo tuần & KPI

## Backend

FastAPI + SQLAlchemy. Xem `backend/README.md` để biết chi tiết (cài đặt,
biến môi trường, dùng Claude thật thay cho `MockProvider`).

```powershell
# từ thư mục gốc repo, virtualenv nằm ở gốc chứ không trong backend/
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".\backend[dev]"
Copy-Item backend\.env.example backend\.env

cd backend
uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

Chạy test backend:

```powershell
cd backend
pytest
```

## Frontend

React + Vite + TypeScript, bốn trang: Thiết lập, Nộp báo cáo, Hàng đợi duyệt,
Dashboard. Xem `frontend/README.md`.

```powershell
cd frontend
npm install
npm run dev     # http://localhost:5173
```

## Kiểm thử trọn vòng

```powershell
.venv\Scripts\python.exe tests\e2e\run_e2e.py
```
