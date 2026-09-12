# Thiết kế: Frontend giai đoạn 2 — bốn trang theo spec §10

Ngày: 2026-09-11
Trạng thái: đã chốt, chờ lập kế hoạch triển khai
Spec gốc: `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md` (§9 API, §10 Frontend)

## 1. Mục tiêu

Dựng frontend React + Vite + TypeScript cho backend đã hoàn thành ở giai đoạn 1,
gồm bốn trang: Thiết lập, Nộp báo cáo, Hàng đợi duyệt, Dashboard. Kết thúc giai
đoạn phải chứng minh được trọn vòng **trên trình duyệt thật**: tạo nhân viên +
KPI → nộp báo cáo → duyệt → dashboard đổi số và tắt cảnh báo.

## 2. Phạm vi

**Trong phạm vi**

- Bốn trang theo §10, `api.ts` mỏng dùng `fetch` thuần, React Router.
- Dropdown "Đang thao tác với tư cách" ở header, lưu `localStorage`.
- Vitest cho tầng hàm thuần; Playwright cho một kịch bản e2e trọn vòng.

**Ngoài phạm vi**

- Đăng nhập, phân quyền (backend không có).
- Xoá Employee / KPI / Task — backend **không có endpoint DELETE**, nên UI
  không có nút xoá.
- react-query hoặc bất kỳ state manager nào (spec §10 chốt là không).
- Sửa backend. Nếu phát sinh bắt buộc phải sửa, dừng lại báo người dùng trước.

## 3. Ràng buộc đã xác minh trên backend

Bốn điều dưới đây đã kiểm bằng cách đọc mã nguồn, không phải phỏng đoán.

| Điều | Kết luận | Bằng chứng |
|---|---|---|
| CORS | Chỉ cho phép origin `http://localhost:5173` | `backend/app/main.py:29` |
| DB cho e2e | Đổi được qua biến môi trường `DATABASE_URL`, không cần sửa backend | `backend/app/config.py:9`, pydantic-settings ưu tiên env var hơn `.env` |
| Blockers | `GET /api/reports` **đã trả kèm** `blockers`, `kpi_suggestions`, `task_suggestions` | `ReportOut` tại `backend/app/schemas.py:120`, dùng làm `response_model` tại `backend/app/routers/reports.py:17` |
| Dạng `detail` khi lỗi | Hai dạng khác nhau | Chuỗi tại `main.py:35/40/45`; mảng lỗi Pydantic tại `main.py:67` |

Hệ quả thiết kế:

- Frontend **phải** được truy cập qua `http://localhost:5173`, không phải
  `127.0.0.1:5173` — cùng một server nhưng khác origin, và origin thứ hai trượt CORS.
  `vite.config.ts` đặt `strictPort: true` để Vite **báo lỗi** thay vì lặng lẽ
  nhảy sang 5174 khi cổng bị chiếm; một lần nhảy cổng như vậy sẽ biểu hiện thành
  lỗi CORS rất khó lần ra nguyên nhân.
- Gọi API sang `http://127.0.0.1:8000` là hợp lệ: CORS xét origin của *trang*, không xét host đích.
- Dashboard lấy blockers từ chính `GET /api/reports`, **một lời gọi**, không N+1.
  Endpoint trả *mọi* báo cáo kèm toàn bộ `raw_text` nên payload phình theo thời
  gian; danh sách đã sắp `id DESC` sẵn (`reports.py:16`) nên client chỉ lấy **5
  báo cáo đầu**.

## 4. Quyết định kiến trúc

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Lấy dữ liệu | Fetch tại từng trang qua hook `useAsync` chung | Không có cache thì không có bug cache cũ. Cache toàn cục sẽ phải tự viết lại phần invalidate của react-query — đúng thứ spec đã loại bỏ |
| State toàn cục | Chỉ duy nhất `currentEmployeeId` | Thứ duy nhất thật sự dùng chung giữa các trang |
| Giao diện | CSS thuần, một `index.css` với CSS variables | Không thêm dependency, đủ cho 4 trang MVP |
| Lỗi API | `ApiError { status, detail }` + `detailToMessage()` | Backend trả `detail` hai dạng; chuẩn hoá một lần ở biên thay vì mỗi trang tự đoán |
| Kiểm thử | Vitest cho hàm thuần, Playwright cho trọn vòng | Backend đã có 129 test nghiệp vụ; không lặp lại |
| Nhớ nhân viên đang chọn | `localStorage` | Giữ qua F5 và qua điều hướng, thuận cho cả thao tác thật lẫn kịch bản Playwright |

## 5. Bố cục

```
frontend/
  package.json  vite.config.ts  tsconfig.json  tsconfig.node.json
  index.html  .gitignore
  src/
    main.tsx  App.tsx  index.css
    types.ts                   # mirror 1-1 backend/app/schemas.py
    api.ts                     # fetch thuần + ApiError
    lib/format.ts              # hàm thuần — bề mặt Vitest
    lib/format.test.ts
    lib/api.test.ts
    lib/useAsync.ts
    context/CurrentEmployee.tsx
    components/  Layout.tsx  EmployeePicker.tsx  StatusBadge.tsx  ErrorBox.tsx
    pages/  SetupPage.tsx  ReportPage.tsx  ReviewPage.tsx  DashboardPage.tsx
tests/e2e/
  run_e2e.py                   # dọn cổng + DB tạm, rồi gọi with_server.py
  full_flow.py                 # kịch bản Playwright
```

Router: `/setup`, `/report`, `/review`, `/dashboard`; `/` chuyển hướng về `/dashboard`.

## 6. Tầng API

`API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'`.

Mọi phản hồi non-2xx ném `ApiError`. Lỗi mạng (backend chưa chạy) ném `ApiError`
với `status = 0` để UI phân biệt được "backend chưa bật" với "backend từ chối",
thay vì hiện `undefined`.

Hàm, khớp 1-1 với §9:

```
listEmployees  createEmployee
listKpis  getKpi  createKpi  updateKpi
listTasks  createTask  updateTask
listReports  getReport  createReport  reextractReport
listSuggestions(status='pending')
approveKpiSuggestion  rejectKpiSuggestion
approveTaskSuggestion  rejectTaskSuggestion
getDashboard
```

## 7. Tầng hàm thuần (`lib/format.ts`)

Đây là nơi Vitest bám vào. Bốn hàm, không chạm DOM, không chạm mạng:

- `detailToMessage(detail)` — nhận chuỗi, mảng lỗi Pydantic, `undefined`, hoặc
  dạng lạ; luôn trả về một câu tiếng Việt hiển thị được.
- `barGeometry(actual, target, expected)` → `{ fillPercent, markerPercent }`,
  cả hai đã clamp 0–100. Lưu ý: phần trăm **hiển thị** không clamp trên 100 (§6
  spec gốc quy định vậy); chỉ hình học thanh tiến độ mới clamp.
- `mondayOf(date)` — đưa một ngày về thứ Hai cùng tuần, để mặc định ô "tuần".
- `formatPercent(value)`.

## 8. Bốn trang

**Thiết lập** — ba khối Employee / KPI / Task, mỗi khối gồm form tạo và bảng
danh sách. Sửa qua PATCH cho KPI và Task. Tạo employee trùng email → 409 hiện
ngay trên form.

**Nộp báo cáo** — chọn nhân viên (mặc định lấy từ header), ô tuần (mặc định thứ
Hai tuần này), textarea, submit. Sau khi nộp hiện panel kết quả: badge
`extraction_status`, danh sách KPI suggestions / task suggestions / blockers.
Nộp trùng `(employee_id, week_start)` → 409 hiện rõ. Trạng thái `failed` → hiện
`extraction_error` kèm nút **Trích lại**; nút này cũng có ở trạng thái
`extracted`, và nếu bị 409 vì báo cáo đã có dòng duyệt thì hiện đúng lý do khoá
(§7.3). Kèm danh sách báo cáo gần đây để mở lại xem.

**Hàng đợi duyệt** — hai bảng tách riêng, đúng hình dạng `SuggestionQueueOut`.
Dòng KPI: ngữ cảnh (tên nhân viên, tuần, evidence) + select KPI (mặc định
`suggested_kpi_id`, để trống nếu `null`) + ô số delta (mặc định
`suggested_delta`) + ô ghi chú + nút Duyệt / Từ chối. Nút Duyệt bị vô hiệu khi
chưa chọn KPI, vì `final_kpi_id` bắt buộc khác `null` (§7.4). Dòng Task:
`raw_text` + select Task + Duyệt / Từ chối. Sau mỗi thao tác reload hàng đợi;
gặp 409 thì hiện thông báo rồi reload.

**Dashboard** — thẻ mỗi KPI: tên, chủ sở hữu, `actual/target unit`, phần trăm,
thanh tiến độ có vạch mốc kỳ vọng, badge `Hoàn thành` / `Đúng tiến độ` /
`Có nguy cơ`. Dưới cùng là blockers gom từ 5 báo cáo gần nhất.

## 9. Kiểm thử

### Vitest

- `lib/format.test.ts` — bốn hàm thuần, gồm các ca biên: `detailToMessage` với
  cả bốn dạng đầu vào; `barGeometry` khi `actual > target` (fill clamp về 100)
  và khi `target = 0`; `mondayOf` khi đầu vào rơi đúng Chủ nhật và đúng thứ Hai.
- `lib/api.test.ts` — `fetch` được stub; kiểm 404/409/422 ném `ApiError` đúng
  `status`, và lỗi mạng cho `status = 0`.

### Playwright — một kịch bản trọn vòng

Chạy bằng `.venv` ở thư mục gốc repo. Dữ liệu chọn sao cho `MockProvider` khớp
được (nó so khớp tên KPI / tiêu đề Task theo chuỗi và lấy **số đầu tiên trên
dòng** làm delta — `backend/app/llm/mock.py`):

1. Tạo nhân viên; tạo KPI `Doanh so` target `100`, kỳ đã trôi phần lớn; tạo task
   `Goi khach hang moi`.
2. **Dashboard lúc này phải là `Có nguy cơ`** — `actual = 0`, `expected` lớn.
   Không kiểm bước này thì bước tắt cảnh báo ở cuối không chứng minh được gì.
3. Nộp báo cáo ba dòng: một dòng chứa tên KPI kèm số, một dòng chứa tiêu đề task,
   một dòng chứa từ khoá vướng mắc. Kiểm đủ ba loại suggestion/blocker xuất hiện.
4. Duyệt, **sửa delta thành 100** trước khi duyệt — qua đó kiểm luôn đường
   `final_*` chứ không phải `suggested_*`.
5. Dashboard: `actual = 100`, badge chuyển `Hoàn thành`, cảnh báo tắt.

### Chạy lặp lại được

Đây là ràng buộc thiết kế, không phải chi tiết vặt. Ba nguồn gây trạng thái rớt
lại giữa hai lần chạy, xử lý cả ba:

- **DB.** Tiến trình uvicorn của e2e nhận `DATABASE_URL` trỏ tới một file SQLite
  riêng, đường dẫn **tuyệt đối** (tránh mơ hồ vì uvicorn chạy với CWD là
  `backend/`). Runner xoá file đó trước mỗi lần chạy; `Base.metadata.create_all`
  trong lifespan tạo lại bảng.
- **Cổng bị chiếm.** `scripts/with_server.py` spawn server bằng `shell=True`, và
  khi dọn dẹp chỉ gọi `terminate()` trên tiến trình đó — trên Windows đó là
  `cmd.exe` bọc ngoài, nên `node.exe` và `python.exe` con sống sót và tiếp tục
  giữ cổng, làm lần chạy thứ hai chết ở `"Server failed to start"`. Không sửa
  script bundled; `run_e2e.py` giải phóng cổng 8000 và 5173 (tra PID rồi
  `taskkill /F /T`) ở **cả trước lẫn sau** khi gọi nó. **Giả thuyết này phải
  được xác minh bằng thực nghiệm** (chạy e2e hai lần liên tiếp), không chấp nhận
  suy luận suông.
- **`localStorage`.** Playwright dùng context mới mỗi lần chạy, nên nhân viên
  đang chọn không rớt lại.

`npm` trên Windows: `with_server.py` dùng `shell=True` nên cmd.exe phân giải
`npm.cmd` bình thường — không cần chỉnh.

Frontend luôn được mở qua `http://localhost:5173` để khớp CORS.

## 10. Rủi ro đã lường

| Rủi ro | Xử lý |
|---|---|
| Vite nhảy cổng 5174 → trượt CORS, lỗi khó đoán | `strictPort: true` |
| `terminate()` không giết tiến trình cháu trên Windows | `run_e2e.py` dọn cổng hai đầu; xác minh bằng hai lần chạy liên tiếp |
| `MockProvider` lấy số **đầu tiên** trên dòng | Câu báo cáo trong e2e viết sao cho số đầu tiên chính là delta mong muốn |
| `venv` cài editable trỏ về checkout gốc | Chạy uvicorn với CWD là `backend/` của worktree; gói `app` phân giải từ CWD trước |
| Payload `GET /api/reports` phình vô hạn | Client chỉ lấy 5 báo cáo đầu (đã sắp `id DESC`) |
