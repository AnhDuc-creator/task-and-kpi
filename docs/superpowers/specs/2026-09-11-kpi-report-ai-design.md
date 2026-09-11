# Thiết kế: Web app AI đọc báo cáo tuần và đề xuất cập nhật tiến độ KPI (MVP)

Ngày: 2026-09-11
Trạng thái: đã chốt, chờ lập kế hoạch triển khai

## 1. Mục tiêu

Nhân viên nộp báo cáo tuần dạng văn bản tự do. Một LLM trích ra các việc đã
xong, các mức tăng tiến độ KPI và các vướng mắc. Quản lý duyệt từng đề xuất;
chỉ đề xuất được duyệt mới làm đổi số liệu. Dashboard hiển thị phần trăm hoàn
thành từng KPI kèm cảnh báo "có nguy cơ" theo một luật cố định.

Tiêu chí thành công của MVP: chạy trọn vòng tạo KPI → nộp báo cáo → duyệt →
dashboard đổi số, với bộ test chạy được mà không cần mạng.

## 2. Phạm vi

**Trong phạm vi**

- Quản lý tối thiểu Employee, KPI, Task.
- Nộp báo cáo tuần dạng văn bản tự do.
- Trích xuất bằng LLM ra JSON `{tasks_done, kpi_updates, blockers}`, validate bằng schema.
- Duyệt từng dòng đề xuất, có sửa số liệu trước khi duyệt.
- Dashboard phần trăm hoàn thành + cảnh báo rủi ro.

**Ngoài phạm vi**

- Đăng nhập, phân quyền, phiên làm việc.
- Triển khai (deploy), hạ tầng, CI/CD.
- Nhiều doanh nghiệp (multi-tenant).
- **KPI kiểu "càng thấp càng tốt"** (ví dụ tỉ lệ lỗi, thời gian xử lý trung
  bình, chi phí). Toàn bộ MVP giả định KPI là loại **càng cao càng tốt**: tiến
  độ cộng dồn về phía chỉ tiêu, và cảnh báo kích hoạt khi thực tế *thấp hơn* kỳ
  vọng. Luật cảnh báo, công thức phần trăm và dấu của `delta_value` đều dựa trên
  giả định này. Hỗ trợ chiều ngược lại sẽ cần thêm trường `direction` trên KPI
  và một nhánh riêng trong `rules.py` — không làm trong MVP.

## 3. Quyết định kiến trúc

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Cách cập nhật tiến độ | Cộng dồn delta | Hợp nhịp báo cáo tuần; giữ được đóng góp từng tuần; dễ hoàn tác |
| Cách khớp đề xuất với KPI | Prompt nhúng catalog KPI, LLM trả `kpi_id` | Ràng buộc được bằng schema; không cần tầng fuzzy-match dễ sai |
| Mức duyệt | Từng dòng, quản lý sửa được | Một dòng LLM sai không làm mất cả báo cáo |
| Vai trò Task | Khớp vào Task có sẵn | Cùng cơ chế catalog với KPI |
| Lưu tiến độ | Sổ cái bất biến, `current_value` tính khi đọc | Một nguồn sự thật duy nhất; lịch sử đầy đủ; logic dễ sai nhất trở thành hàm thuần |
| Provider LLM | MockProvider (mặc định) + AnthropicProvider | Test chạy không cần mạng; chỉ một adapter thật phải bảo trì |

## 4. Kiến trúc tổng thể

```
frontend/ (React + Vite + TS)  ──HTTP/JSON──►  backend/ (FastAPI)
                                                 ├── routers/    (HTTP, không chứa logic)
                                                 ├── services/   (extraction, approval, dashboard)
                                                 ├── rules.py    (luật cảnh báo — hàm thuần)
                                                 ├── llm/        (interface + mock + adapter Anthropic)
                                                 └── models.py   (SQLAlchemy → SQLite)
```

Nguyên tắc phân tách:

- `routers` chỉ dịch HTTP ↔ service, không chứa quyết định nghiệp vụ.
- `services` giữ toàn bộ nghiệp vụ; đây là nơi giao dịch (transaction) bắt đầu và kết thúc.
- `rules.py` là hàm thuần, không chạm database, nhận "hôm nay" qua tham số.
- `llm/` không biết gì về SQLAlchemy: nhận Pydantic vào, trả Pydantic ra.

## 5. Mô hình dữ liệu

### employees
`id, name, email, created_at`

### kpis
`id, name, target_value (float), unit (str), owner_id → employees.id,
period_start (date), period_end (date), created_at`

Ràng buộc: `period_end >= period_start`, `target_value > 0`.

### tasks
`id, title, kpi_id → kpis.id, assignee_id → employees.id,
status ENUM(todo, doing, done), completed_at (nullable), created_at`

### weekly_reports
`id, employee_id → employees.id, week_start (date), raw_text,
submitted_at, extraction_status ENUM(pending, extracted, failed),
extraction_error (nullable), provider_name (nullable),
raw_llm_response (text, nullable)`

**Ràng buộc UNIQUE `(employee_id, week_start)`** — mỗi nhân viên một báo cáo cho
mỗi tuần. Vi phạm trả HTTP 409 (mục 7.1).

### kpi_update_suggestions
`id, report_id → weekly_reports.id,
suggested_kpi_id (nullable, → kpis.id), suggested_delta (float), evidence (text),
status ENUM(pending, approved, rejected),
final_kpi_id (nullable, → kpis.id), final_delta (float, nullable),
review_note (nullable), reviewed_at (nullable), created_at`

### task_completion_suggestions
`id, report_id → weekly_reports.id,
suggested_task_id (nullable, → tasks.id), raw_text,
status ENUM(pending, approved, rejected),
final_task_id (nullable, → tasks.id), reviewed_at (nullable), created_at`

### blockers
`id, report_id → weekly_reports.id, description, related_kpi_id (nullable, → kpis.id)`

### kpi_progress_entries
`id, kpi_id → kpis.id, delta_value (float), source_suggestion_id → kpi_update_suggestions.id,
effective_date (date), created_at`

### Quy ước

- Trường `suggested_*` là bản gốc LLM đưa ra và **không bao giờ bị ghi đè**.
  Sửa của quản lý đi vào `final_*`. Nhờ vậy đo được độ chính xác của AI sau này
  mà không cần thêm bảng.
- `kpi_progress_entries` **chỉ được ghi thêm**, và chỉ bởi service duyệt.
- `current_value(kpi) = SUM(kpi_progress_entries.delta_value WHERE kpi_id = kpi.id)`.
  Không có cột `current_value` trên bảng `kpis`.
- Blockers chỉ lưu và hiển thị, không có luồng duyệt — chúng không làm đổi số liệu.

## 6. Luật cảnh báo rủi ro

Đặt trong `rules.py`, là hàm thuần. Ngưỡng `0.8` là hằng số có tên
(`RISK_THRESHOLD`), không rải số trực tiếp trong code.

```
elapsed_ratio = clamp((today - period_start) / (period_end - period_start), 0, 1)
expected      = target_value * elapsed_ratio
at_risk       = expected > 0 and actual < RISK_THRESHOLD * expected
percent       = actual / target_value        (dùng để hiển thị, không chặn trên 100%)

status = completed  nếu actual >= target_value
       | at_risk    nếu at_risk
       | on_track   còn lại
```

Các ca biên, quy định rõ:

- Kỳ chưa bắt đầu (`today < period_start`) → `elapsed_ratio = 0` → `expected = 0`
  → không cảnh báo.
- Kỳ đã kết thúc (`today > period_end`) → `elapsed_ratio = 1` → `expected = target_value`.
- `period_end == period_start` → `elapsed_ratio = 1` (tránh chia cho 0).
- `actual >= target_value` → `completed`, kể cả khi vẫn dưới `expected`. Thứ tự
  kiểm tra được quy định để kết quả luôn xác định.

"Hôm nay" được **tiêm vào hàm qua tham số**, không gọi `date.today()` bên trong,
để test không phụ thuộc ngày chạy.

## 7. Luồng nghiệp vụ

### 7.1 Nộp báo cáo

1. `POST /api/reports` với `employee_id`, `week_start`, `raw_text`.
2. Nếu đã tồn tại báo cáo cho `(employee_id, week_start)` → **HTTP 409**, không tạo gì.
3. Tạo `weekly_reports` với `extraction_status = pending`.
4. Chạy trích xuất **đồng bộ** ngay trong request (mục 7.2). Không hàng đợi, không worker.
5. Trả về báo cáo kèm các suggestion vừa sinh.

### 7.2 Trích xuất

1. Dựng `ExtractionRequest` gồm `report_text`, catalog KPI đang mở của nhân viên,
   catalog Task chưa `done` của nhân viên.
2. Gọi `provider.extract(request)`.
3. Validate kết quả bằng schema Pydantic (mục 8).
4. Thành công → tạo các suggestion và blocker, đặt `extraction_status = extracted`.
5. Thất bại (JSON hỏng, validate trượt, lỗi provider) → `extraction_status = failed`,
   lưu thông điệp lỗi vào `extraction_error`, **không tạo suggestion nào**. Hàng
   đợi duyệt không bao giờ nhận dữ liệu rác.

### 7.3 Trích lại

`POST /api/reports/{id}/extract`.

**Điều kiện cho phép** — thoả *một trong hai*:

- `extraction_status = failed`; hoặc
- báo cáo **chưa có suggestion nào ở trạng thái `approved`**. Điều kiện này quét
  **cả hai bảng** `kpi_update_suggestions` và `task_completion_suggestions`: chỉ
  cần một dòng `approved` ở một trong hai bảng là điều kiện không thoả.

Ngược lại → **HTTP 409**, không thay đổi gì. Trên thực tế, điều này có nghĩa: chỉ
cần một dòng đã được duyệt là báo cáo bị khoá khỏi việc trích lại, vì số liệu đã
đi vào sổ cái và một lần trích lại sẽ khiến đề xuất trong sổ cái không còn khớp
với đề xuất đang hiển thị.

**Tác động khi được phép:**

- **Xoá** mọi suggestion `pending` của báo cáo đó (cả KPI lẫn task).
- **Xoá** mọi blocker của báo cáo đó rồi tạo lại từ kết quả mới.
- **Giữ nguyên** các suggestion `rejected` để lưu vết quyết định của quản lý.
- Chạy lại mục 7.2 và cập nhật `extraction_status`, `extraction_error`,
  `provider_name`, `raw_llm_response`.

### 7.4 Duyệt

`POST /api/suggestions/kpi/{id}/approve` với `final_kpi_id`, `final_delta`, `note`:

1. Nếu suggestion không còn `pending` → **HTTP 409** (thao tác idempotent, không
   thể cộng delta hai lần).
2. Ghi `final_*`, đặt `status = approved`, `reviewed_at = now`.
3. Tạo một dòng `kpi_progress_entries` với `kpi_id = final_kpi_id`,
   `delta_value = final_delta`, `source_suggestion_id = suggestion.id`,
   `effective_date = report.week_start`.

Bước 2 và bước 3 nằm trong **một giao dịch duy nhất**: đổi `status` và ghi dòng
`kpi_progress_entries` cùng commit hoặc cùng rollback. Không bao giờ tồn tại
trạng thái suggestion đã `approved` mà sổ cái thiếu dòng tương ứng, hay ngược lại.

`final_kpi_id` bắt buộc phải khác `null` khi duyệt — đây là chỗ quản lý gán KPI
cho những đề xuất LLM trả về `kpi_id = null`.

`POST /api/suggestions/kpi/{id}/reject`: đặt `status = rejected`, không sinh dòng
sổ cái nào.

`POST /api/suggestions/task/{id}/approve` với `final_task_id`: ghi `final_task_id`,
đặt `status = approved`, rồi đặt `tasks.status = done` và `tasks.completed_at = now`
cho task đó. `final_task_id` bắt buộc khác `null` — đây là chỗ quản lý gán task
cho đề xuất LLM trả về `task_id = null`, hoặc sửa lại khi LLM khớp nhầm. Từ chối
thì không đổi gì trên bảng `tasks`. Cùng luật 409 khi suggestion không còn `pending`.

Việc đổi `status` của suggestion và cập nhật `tasks` cũng nằm trong **một giao
dịch duy nhất**, theo cùng nguyên tắc như duyệt suggestion KPI.

Duyệt một task đã ở trạng thái `done` là hợp lệ và không có tác dụng phụ nào
ngoài việc ghi nhận suggestion — `completed_at` giữ nguyên giá trị cũ.

## 8. Tầng LLM

### Interface

```python
class LlmProvider(Protocol):
    name: str
    def extract(self, request: ExtractionRequest) -> ExtractionResult: ...
```

`ExtractionRequest`: `report_text`, `kpi_catalog: list[KpiCatalogItem]`,
`task_catalog: list[TaskCatalogItem]`.

### Schema kết quả

```json
{
  "tasks_done":  [{ "task_id": 12, "description": "..." }],
  "kpi_updates": [{ "kpi_id": 7, "delta_value": 5, "evidence": "trích nguyên văn từ báo cáo" }],
  "blockers":    [{ "description": "...", "related_kpi_id": 7 }]
}
```

`task_id`, `kpi_id`, `related_kpi_id` được phép `null` khi LLM không chắc.

Validator từ chối:

- `kpi_id` / `task_id` / `related_kpi_id` không `null` nhưng không nằm trong catalog đã gửi.
- `delta_value` không phải số hữu hạn (NaN, vô cực).
- JSON không parse được hoặc thiếu khoá bắt buộc.

Mọi trường hợp trượt đều dẫn tới `extraction_status = failed` như mục 7.2.

### Các provider

- **MockProvider** — mặc định, không dùng mạng. Khớp từ khoá tên KPI/Task trong
  catalog và bắt số bằng regex; đủ thật để test trọn vòng có ý nghĩa. Nhận được
  kịch bản đóng sẵn khi unit test cần một kết quả cụ thể (kể cả kết quả hỏng).
- **AnthropicProvider** — SDK `anthropic`, model `claude-opus-5`, ép JSON đúng
  schema bằng **structured outputs**: `client.messages.parse(...,
  output_format=ExtractionResult)` trả về `response.parsed_output` đã là một
  `ExtractionResult` hợp lệ. Đọc `ANTHROPIC_API_KEY` từ `.env`.
  `stop_reason == "refusal"` được coi là lỗi trích xuất (→ `failed`), giống mọi
  lỗi provider khác.

Chọn qua `LLM_PROVIDER=mock|anthropic` trong `.env`, mặc định `mock`. Test không
bao giờ chạm provider thật.

## 9. API

```
GET/POST         /api/employees
GET/POST/PATCH   /api/kpis            GET /api/kpis/{id}
GET/POST/PATCH   /api/tasks
POST             /api/reports                        # 409 nếu trùng (employee_id, week_start)
GET              /api/reports    GET /api/reports/{id}
POST             /api/reports/{id}/extract           # 409 nếu vi phạm điều kiện mục 7.3
GET              /api/suggestions?status=pending    # trả {kpi_updates: [...], task_completions: [...]}
POST             /api/suggestions/kpi/{id}/approve   # body: final_kpi_id, final_delta, note
POST             /api/suggestions/kpi/{id}/reject
POST             /api/suggestions/task/{id}/approve  # body: final_task_id
POST             /api/suggestions/task/{id}/reject
GET              /api/dashboard                      # mỗi KPI: actual, target, percent, expected, status
```

`GET /api/suggestions` trả **hai danh sách tách riêng** (`kpi_updates` và
`task_completions`) chứ không trộn chung, vì hai loại có hình dạng và thao tác
duyệt khác nhau. Mỗi phần tử kèm `report_id`, `employee_name` và `week_start` để
trang duyệt hiển thị được ngữ cảnh mà không phải gọi thêm.

Quy ước mã lỗi: `404` không tìm thấy, `409` xung đột trạng thái (trùng báo cáo,
trích lại bị khoá, duyệt lại suggestion đã xử lý), `422` dữ liệu vào sai.

## 10. Frontend

React + Vite + TypeScript, React Router, một `api.ts` mỏng dùng fetch thuần
(không react-query ở MVP). Bốn trang:

1. **Thiết lập** — CRUD tối thiểu Employee / KPI / Task.
2. **Nộp báo cáo** — chọn nhân viên + tuần, textarea, submit, xem ngay kết quả
   trích xuất; hiển thị rõ lỗi khi trích xuất thất bại kèm nút trích lại.
3. **Hàng đợi duyệt** — suggestion đang chờ, sửa `delta` và gán `kpi` ngay tại
   dòng, nút duyệt / từ chối.
4. **Dashboard** — thẻ từng KPI: phần trăm hoàn thành, thanh tiến độ có mốc kỳ
   vọng, nhãn `Có nguy cơ`; kèm danh sách blockers gần đây.

Không có đăng nhập: header có dropdown "Đang thao tác với tư cách" để chọn nhân
viên, và trang duyệt mở tự do.

## 11. Kiểm thử (pytest)

- **`rules.py`**: các ca biên của `elapsed_ratio` (trước kỳ, trong kỳ, sau kỳ,
  kỳ dài 0 ngày) và ngưỡng 80% (ngay dưới, đúng tại, ngay trên).
- **Schema**: JSON hỏng, `kpi_id` ngoài catalog, `delta_value` vô hạn, thiếu
  khoá → đều bị chặn và báo cáo chuyển `failed` mà không sinh suggestion.
- **Service duyệt**: duyệt cộng đúng delta; từ chối không cộng; sửa rồi duyệt
  dùng `final_*` chứ không dùng `suggested_*`; duyệt hai lần chỉ cộng một lần (409).
- **Nộp trùng**: nộp lại cùng `(employee_id, week_start)` trả 409 và không tạo
  báo cáo thứ hai.
- **Trích lại** (ca riêng theo mục 7.3):
  - báo cáo `failed` → trích lại được;
  - báo cáo `extracted` chưa có dòng nào duyệt → trích lại được, suggestion
    `pending` cũ biến mất, suggestion `rejected` cũ còn nguyên, blockers được tạo lại;
  - báo cáo đã có ít nhất một suggestion `approved` → 409, không suggestion nào
    bị xoá và sổ cái không đổi.
- **API** qua `TestClient`, SQLite in-memory dựng lại từng test, `LLM_PROVIDER=mock`.
- **Trọn vòng**: tạo KPI → nộp báo cáo → duyệt → dashboard đổi số và tắt cảnh báo.

## 12. Bố cục dự án

```
backend/
  app/
    main.py  config.py  db.py  models.py  schemas.py  rules.py
    llm/       base.py  mock.py  anthropic_provider.py  prompt.py
    services/  extraction.py  approval.py  dashboard.py
    routers/   employees.py  kpis.py  tasks.py  reports.py  suggestions.py  dashboard.py
  tests/
frontend/
  src/  pages/  components/  api.ts
docs/superpowers/specs/
```
