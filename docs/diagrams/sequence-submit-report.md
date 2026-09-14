# Sơ đồ tuần tự — `POST /api/reports` (nộp báo cáo tuần)

Nguồn sự thật: `backend/app/routers/reports.py:23`, `backend/app/services/extraction.py:106`
(`submit_report` → `run_extraction` → `build_extraction_request`), `backend/app/llm/base.py:62`
(`validate_extraction_result`), `backend/app/main.py:35` (các bộ xử lý lỗi).

```mermaid
sequenceDiagram
    autonumber
    actor FE as ReportPage.tsx
    participant API as main.py + routers/reports.py
    participant SVC as services/extraction.py
    participant PROV as llm provider<br/>Mock hoặc Anthropic
    participant VAL as base.validate_extraction_result
    participant DB as SQLite<br/>SQLAlchemy Session

    FE->>API: POST /api/reports<br/>employee_id, week_start, raw_text
    Note over API: Pydantic ReportCreate<br/>raw_text min_length 1<br/>sai thì 422

    API->>DB: db.get Employee, employee_id
    alt không tìm thấy nhân viên
        DB-->>API: None
        API-->>FE: 404 NotFoundError
    end

    API->>SVC: submit_report db, employee_id, week_start, raw_text, provider
    SVC->>DB: SELECT weekly_reports<br/>WHERE employee_id AND week_start

    alt đã có báo cáo cho tuần đó
        DB-->>SVC: WeeklyReport
        SVC-->>API: raise ConflictError
        API-->>FE: 409 Nhân viên này đã nộp báo cáo cho tuần đó
        Note over DB: Không ghi gì. Kiểm tra bằng SELECT<br/>trước, không dựa vào UNIQUE constraint
    else chưa có
        DB-->>SVC: None
        SVC->>DB: INSERT weekly_reports<br/>extraction_status = pending
        SVC->>DB: commit + refresh

        SVC->>SVC: run_extraction db, report, provider
        SVC->>DB: SELECT kpis WHERE owner_id = employee_id
        SVC->>DB: SELECT tasks WHERE assignee_id = employee_id<br/>AND status != done
        Note over SVC: build_extraction_request<br/>dựng catalog KPI và Task

        SVC->>SVC: report.provider_name = provider.name

        SVC->>PROV: extract ExtractionRequest

        alt LLM hỏng — ExtractionError hoặc ValidationError
            PROV--xSVC: raise ExtractionError<br/>lỗi mạng, refusal, không có parsed_output
            SVC->>DB: UPDATE extraction_status = failed<br/>extraction_error = str exc
            SVC->>DB: commit
            Note over SVC,DB: KHÔNG tạo suggestion nào.<br/>Hàng đợi duyệt không nhận dữ liệu rác
            SVC-->>API: WeeklyReport status = failed
            API-->>FE: 201 Created, extraction_status = failed
            Note over FE: Vẫn là 201, KHÔNG phải lỗi HTTP.<br/>UI hiện extraction_error kèm nút Trích lại
        else LLM trả kết quả
            PROV-->>SVC: ExtractionResult<br/>tasks_done, kpi_updates, blockers
            SVC->>VAL: validate_extraction_result result, request

            alt id ngoài catalog hoặc delta không hữu hạn
                VAL--xSVC: raise ExtractionError
                SVC->>DB: UPDATE extraction_status = failed<br/>extraction_error
                SVC->>DB: commit
                SVC-->>API: WeeklyReport status = failed
                API-->>FE: 201 Created, extraction_status = failed
            else hợp lệ
                VAL-->>SVC: None
                loop mỗi kpi_update
                    SVC->>DB: INSERT kpi_update_suggestions<br/>suggested_kpi_id, suggested_delta, evidence<br/>status = pending
                end
                loop mỗi task_done
                    SVC->>DB: INSERT task_completion_suggestions<br/>suggested_task_id, raw_text, status = pending
                end
                loop mỗi blocker
                    SVC->>DB: INSERT blockers<br/>description, related_kpi_id
                end
                SVC->>DB: UPDATE extraction_status = extracted<br/>extraction_error = null<br/>raw_llm_response = result JSON
                SVC->>DB: commit + refresh
                SVC-->>API: WeeklyReport
                API-->>FE: 201 Created, ReportOut<br/>kèm kpi_suggestions, task_suggestions, blockers
            end
        end
    end
```

## Giải thích

- **Trích xuất chạy đồng bộ ngay trong request.** Không hàng đợi, không worker: `submit_report`
  gọi thẳng `run_extraction` trước khi trả về, nên response đã kèm sẵn các suggestion.
- **Nhánh 409 xảy ra *trước* khi ghi bất cứ thứ gì.** `submit_report` kiểm bằng một `SELECT`
  rồi mới `INSERT`, nên khi trùng tuần thì không có hàng nào được tạo.
- **Nhánh LLM hỏng không làm hỏng request.** `run_extraction` bắt `(ExtractionError, ValidationError)`,
  đặt `extraction_status = failed`, lưu thông điệp lỗi và **commit** — báo cáo vẫn tồn tại,
  endpoint vẫn trả **201**. Client phân biệt thành/bại qua trường `extraction_status`, không qua mã HTTP.
- **Validator nằm ở tầng service, không ở tầng provider.** `validate_extraction_result` được gọi
  ngay sau `provider.extract(...)` cho **mọi** provider, nên không provider nào tự miễn trừ được
  ràng buộc "id phải trong catalog" và "delta phải hữu hạn".
- **`ValidationError` của Pydantic cũng bị bắt.** Một provider ném lỗi Pydantic (ví dụ
  `delta_value` vô hạn chặn bởi `allow_inf_nan=False`) sẽ khiến báo cáo thành `failed`,
  chứ không làm sập request thành 500.

## Chỗ đã đồng bộ

1. **JSON hỏng / thiếu khoá không đi qua validator.** Spec §8 trước đây xếp chúng vào phần
   việc của `validate_extraction_result`; thực tế validator chỉ kiểm hai bất biến (id trong
   catalog, delta hữu hạn), còn JSON hỏng do `AnthropicProvider` bọc thành `ExtractionError`
   và thiếu khoá nổi lên thành `ValidationError` của Pydantic. **Đã sửa spec theo code:**
   §8 giờ mô tả đúng ba đường, và nói rõ cả ba đều về `failed`.

## Còn lại, đã ghi nhận chứ chưa sửa

- **Check-then-insert.** Spec §5 + §7.1 nói ràng buộc trùng tuần là
  `UNIQUE (employee_id, week_start)` và "vi phạm trả 409"; code kiểm bằng `SELECT` trước
  (`extraction.py:114`) rồi mới `INSERT`. Hai request đồng thời lọt qua cả hai lần `SELECT`,
  và request thua cuộc nhận `IntegrityError` không được bắt → **500 thay vì 409**.
  `services/employee.py` có đúng cùng dạng này với email trùng. Đã ghi vào mục
  "Hạn chế đã biết" của README kèm cách sửa đúng; MVP chấp nhận đánh đổi.
- **`routers/reports.py:29` tự kiểm `db.get(Employee, ...)`** và tự ném `NotFoundError` —
  một quyết định nghiệp vụ nằm trong router, giống ba router CRUD trước khi được tách.
  Để ngoài phạm vi lần này vì nó nằm trên đường trích xuất.
- **`services/extraction.py` chưa theo idiom giao dịch chung của tầng service.**
  Năm module service còn lại (`approval.py`, `employee.py`, `kpi.py`, `task.py`) đều bọc
  `db.commit()` trong `try` / `except` → `rollback` → `raise`; ba lệnh `db.commit()` ở
  `extraction.py:101,127,180` thì commit trần, không có khối đó. Ghi nhận là module
  duy nhất lệch khỏi mẫu này, chưa sửa trong lần này.
