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

## Hạn chế đã biết

- **Check-then-insert: hai request đồng thời cho 500 thay vì 409.**
  `POST /api/employees` (email trùng) và `POST /api/reports` (trùng
  `employee_id` + `week_start`) đều kiểm bằng một `SELECT` trước rồi mới `INSERT`.
  Ràng buộc `UNIQUE` ở tầng DB vẫn là lưới đỡ cuối cùng, nhưng hai request đến
  cùng lúc sẽ cùng lọt qua vòng `SELECT`; request thua cuộc nhận `IntegrityError`
  không được bắt và thoát ra thành **HTTP 500** thay vì **409** như spec quy định.
  Với một tổ nhỏ nhập liệu bằng tay thì xác suất này gần bằng không nên MVP chấp
  nhận đánh đổi; cách sửa đúng là bắt `IntegrityError` quanh `commit` rồi dịch
  thành `ConflictError`, và bỏ hẳn vòng `SELECT` kiểm trước.

- **`CheckConstraint` chỉ áp cho database tạo mới.** Dự án dùng
  `Base.metadata.create_all` chứ không có migration, nên hai ràng buộc
  `period_end >= period_start` và `target_value > 0` trên bảng `kpis` chỉ tồn tại
  trong database được tạo sau thay đổi này. Một file `kpi.db` cũ phải xoá đi cho
  tạo lại mới có chúng. SQLite không có `ALTER TABLE ADD CONSTRAINT`, nên không
  có đường nâng cấp tại chỗ: nếu dữ liệu cũ còn giá trị, phải build lại bảng
  bằng tay (tạo bảng mới, copy dữ liệu, xoá bảng cũ, đổi tên) thay vì chỉ xoá
  `kpi.db`.
