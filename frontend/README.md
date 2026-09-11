# Frontend — báo cáo tuần & KPI

## Chạy lần đầu

```powershell
cd frontend
npm install
```

## Chạy dev server

```powershell
cd frontend
npm run dev
```

Mở **http://localhost:5173**. Backend chỉ mở CORS cho đúng origin này —
`127.0.0.1:5173` sẽ bị chặn. Cổng được ghim cứng (`strictPort`), nên nếu 5173
đang bận thì Vite báo lỗi thay vì nhảy sang cổng khác.

Backend phải chạy song song ở cổng 8000:

```powershell
cd backend
uvicorn app.main:app --reload
```

Đổi địa chỉ backend bằng biến môi trường `VITE_API_BASE` nếu cần.

## Test

```powershell
cd frontend
npm test          # Vitest — tầng hàm thuần và tầng API
```

Trọn vòng trên trình duyệt thật (tự khởi động cả hai server, dùng một database
SQLite tạm nên chạy lại được bao nhiêu lần cũng được). Kịch bản dùng
Playwright, chưa nằm trong file phụ thuộc nào nên cần cài một lần (venv ở
gốc repo, không phải trong `frontend/`):

```powershell
.venv\Scripts\python.exe -m pip install playwright
.venv\Scripts\python.exe -m playwright install chromium
```

Chạy từ thư mục gốc repo (không phải từ `frontend/`):

```powershell
.venv\Scripts\python.exe tests\e2e\run_e2e.py
```

**Lưu ý:** kịch bản trên tự giải phóng cổng 8000 và 5173 trước và sau khi
chạy, nhưng chỉ kill tiến trình mà nó nhận ra là server của chính nó
(uvicorn / Vite dev server). Nếu cổng đang bị một tiến trình khác giữ, script
sẽ **từ chối chạy** và in cảnh báo tên cổng + PID — hãy tự giải phóng cổng đó
rồi chạy lại, thay vì để script kill nhầm tiến trình của bạn.
