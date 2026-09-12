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

Kịch bản e2e dùng Playwright. Gói Python đã nằm trong dev-extras nên
`pip install -e ".\backend[dev]"` ở trên đã cài sẵn; chỉ còn phải tải trình
duyệt một lần:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
```

```powershell
.venv\Scripts\python.exe tests\e2e\run_e2e.py
```

**Lưu ý:** kịch bản trên tự giải phóng cổng 8000 và 5173 trước và sau khi
chạy, nhưng chỉ kill tiến trình mà nó nhận ra là server của chính nó
(uvicorn / Vite dev server). Nếu cổng đang bị một tiến trình khác giữ (ví
dụ bạn đang tự chạy `uvicorn --reload` ở cửa sổ khác), script sẽ **từ chối
chạy** và in cảnh báo tên cổng + PID — hãy tự giải phóng cổng đó rồi chạy
lại, thay vì để script kill nhầm tiến trình của bạn. Sau khi chạy xong,
nếu gặp tiến trình lạ thì script chỉ cảnh báo chứ không đổi kết quả của
lần chạy vừa rồi.
