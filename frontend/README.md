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
SQLite tạm nên chạy lại được bao nhiêu lần cũng được):

```powershell
.venv\Scripts\python.exe tests\e2e\run_e2e.py
```
