# Review toàn nhánh — Backend Giai đoạn 1

Ngày: 2026-09-11
Phạm vi: `afe96f1..9068de5` (14 task, toàn bộ `backend/`)
Spec ràng buộc: `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md`
Kết luận: **Merge sau khi sửa** — các lỗi đã được sửa trong `9068de5..92c1c78` và re-review xác nhận sạch.

Reviewer chạy ba lượt: đọc toàn bộ cây `backend/`, lần bốn luồng nghiệp vụ qua code
thật, rồi chạy bộ test cùng 11 đột biến và 4 phép thử HTTP đối kháng trên một bản sao.

---

## Kết luận

> Kiến trúc vững và các bất biến đứng vững ở mọi chỗ tôi tấn công được, nhưng một lỗ
> hổng cho phép quản lý ghi một delta không hữu hạn thẳng vào sổ cái chỉ-ghi-thêm,
> âm thầm và không thể hoàn tác, làm sai lệch một KPI.

---

## Độ phủ spec

| § | Trạng thái | Bằng chứng |
|---|---|---|
| 1 Mục tiêu | Đã làm (phần backend) | `tests/test_end_to_end.py:8` chạy KPI → báo cáo → duyệt → dashboard qua HTTP; 122 pass / 0 skip trong 4.4s, không mạng |
| 2 Phạm vi | Đã làm | Không có trường `direction`, không có nhánh "càng thấp càng tốt" trong `rules.py` |
| 3 Quyết định kiến trúc | Đã làm, cả sáu | Cộng dồn delta, catalog trong prompt (`llm/prompt.py:21`), duyệt từng dòng, catalog task, sổ cái, mock mặc định |
| 4 Phân tầng | Đã làm | `HTTPException` trong `app/`: **0 kết quả**. `date.today()` trong `app/`: **đúng 1 lần** (`routers/dashboard.py:16`). `rules.py` không chạm DB. `llm/` không import SQLAlchemy |
| 5 Mô hình dữ liệu | Đã làm, 2 sai lệch | Đủ 8 bảng, `UniqueConstraint` tại `models.py:105`, không có cột `current_value`. **Sai lệch A:** `source_suggestion_id` nullable nhưng spec không đánh dấu. **Sai lệch B:** ràng buộc `kpis` chỉ có ở Pydantic, không ở DB |
| 6 Luật cảnh báo | Đã làm | `RISK_THRESHOLD` có tên, `today` được tiêm, cả bốn ca biên có test |
| 7.1 Nộp báo cáo | Đã làm | 409 trước mọi insert (`extraction.py:114-121`) |
| 7.2 Trích xuất | Đã làm, 1 lỗ | Đồng bộ, cổng gọi từ service. Xoá lời gọi cổng → 3 test đỏ. **Lỗ:** chỉ bắt `ExtractionError` và `ValidationError`; ngoại lệ khác thoát thành 500 và để báo cáo ở `pending`. Cả hai provider hiện có đều an toàn nên đây là tiềm ẩn |
| 7.3 Trích lại | Đã làm, chính xác | Điều kiện tại `extraction.py:160-166` là De Morgan của spec; quét cả hai bảng. Xoá guard → 4 test đỏ; xoá luôn dòng rejected → 1 test đỏ |
| 7.4 Duyệt | Đã làm | Một giao dịch có rollback; 409 khi không còn pending; sổ cái xây từ `final_*` (đổi sang `suggested_*` → 2 đỏ); `suggested_*` bất biến (ghi đè → 3 đỏ); `effective_date` từ `week_start` (dùng today → 1 đỏ) |
| 8 Tầng LLM | Đã làm | Protocol, schema, cả ba nhánh từ chối của validator đều có test, gồm hai ca bypass Pydantic bằng `model_construct`. `stop_reason == "refusal"` được xử lý |
| 9 API | Đã làm, vi phạm kỷ luật mã lỗi | Đủ route đúng hình dạng. 404/409/422 đúng **trừ** số thực không hữu hạn (xem Critical) |
| 10 Frontend | Không thuộc nhánh này | Giai đoạn 1 chỉ backend |
| 11 Kiểm thử | Đã làm, 1 lỗ thật | Đủ ca đã liệt kê. Lỗ: đường trích xuất thất bại không có coverage mức HTTP |
| 12 Bố cục | Đã làm | Khớp, cộng `dependencies.py`, `errors.py`, `llm/factory.py` — đều chính đáng |

### Ghi chú về §6 (không phải lỗi)

Spec nói thứ tự kiểm `completed`/`at_risk` "được quy định để kết quả luôn xác định".
Điều đó **không quan sát được**: `at_risk` cần `actual < 0.8·expected` và
`expected = target·ratio ≤ target` (vì `compute_elapsed_ratio` kẹp về 1), nên
`actual ≥ target` buộc `at_risk` sai. Hai nhánh loại trừ nhau. Đột biến đảo thứ tự
để lại cả 122 test xanh — đó là *equivalent mutant*, không phải lỗ hổng coverage.
Đáng biết rằng cách phá hoà này là **không thể test**, chứ không phải chưa test.

---

## Kiểm bốn luồng xuyên suốt

**nộp → trích → duyệt → dashboard.** Đứng vững. Xác nhận dashboard đọc
`SUM(delta_value)` sống chứ không phải cache: duyệt 60 trên chỉ tiêu 100 làm
`actual_value` 0 → 60 và lật `at_risk` true → false trong cùng session.

**nộp → trích xuất thất bại → trích lại.** Đứng vững ở tầng service. Khi thất bại,
`run_extraction` đặt `failed` + `extraction_error` và **return trước mọi `db.add`**,
nên hàng đợi duyệt không bao giờ nhận rác. Nhưng luồng này **chưa từng đi qua HTTP**.

**duyệt → thử trích lại (phải bị chặn).** Đứng vững, kiểm đối kháng: sau khi duyệt,
`POST /api/reports/{id}/extract` trả 409 và duyệt lại cũng 409.

**Bất biến dưới tổ hợp.** Đi tìm tổ hợp phá được một trong ba, không tìm thấy:
- *Sổ cái chỉ-ghi-thêm*: `KpiProgressEntry` chỉ được dựng tại `approval.py:64`. Không UPDATE, không DELETE, không cascade chạm tới.
- *`suggested_*` bất biến*: chỉ `run_extraction` ghi; duyệt chỉ ghi `final_*`.
- *Duyệt idempotent*: cả hai `_load_pending_*` ném `ConflictError` trước mọi thay đổi.
- *Đếm trùng*: không thể lấy hai dòng sổ cái từ một tuần — duyệt khoá báo cáo khỏi trích lại, và trích lại xoá dòng pending trước khi dòng mới tồn tại.

Tổ hợp duy nhất phá được bất biến phá bằng **giá trị**, không phải thứ tự — xem Critical.

---

## Phát hiện

### Critical — delta không hữu hạn làm sai lệch sổ cái vĩnh viễn

`app/schemas.py` (`KpiApproveIn.final_delta`)

`app/llm/base.py:41` chặn delta của **LLM** bằng `Field(allow_inf_nan=False)`, và
`validate_extraction_result` kiểm hữu hạn lần thứ hai cho provider bỏ qua Pydantic.
Delta của **quản lý** — con số thật sự tới sổ cái — không được cả hai chặn.

Tái hiện end-to-end (`1e400` là JSON hợp lệ bình thường, Python đọc thành `inf`):

```
POST /api/suggestions/kpi/1/approve   {"final_kpi_id": 1, "final_delta": 1e400}
  -> HTTP 200, body báo "final_delta": null
  -> kpi_progress_entries: [(kpi_id=1, delta_value=inf)]
GET /api/dashboard
  -> {"actual_value": null, "percent_complete": null,
      "status": "completed", "at_risk": false}     # chỉ tiêu là 100
```

Một KPI ở 0% được báo là **`completed`** với actual null và cảnh báo tắt. Phản hồi
nói với quản lý `"final_delta": null`, nên giá trị lưu và giá trị báo lệch nhau mà
không có gì trông bất thường tại chỗ gọi.

**Không hoàn tác được qua API:** `POST /api/reports/{id}/extract` → 409 (báo cáo đã
khoá), duyệt lại → 409, và bù `-1e400` cũng vô ích vì `inf + -inf = nan`. Phải chạy
SQL trực tiếp vào chính cái sổ cái mà thiết kế tuyên bố bất biến.

### Important 1 — cùng lỗ hổng, hai endpoint khác trả 500 thay vì 422

- `approve` với `NaN` → SQLite lưu NaN thành NULL → `IntegrityError` → **500**. (`db.rollback()` làm đúng việc: suggestion vẫn `pending`, sổ cái vẫn trống. Chỉ sai mã trạng thái, không hỏng dữ liệu.)
- `POST /api/kpis` với `NaN` → Pydantic từ chối đúng, nhưng handler validation-error của FastAPI sập khi serialize `'input': nan` → **500**. Chính phản hồi 422 bị sập.
- `POST /api/kpis` với `1e400` → **201 Created**, vì `gt=0` đúng với `inf`. Mọi phản hồi sau đó báo `"target_value": null`.

### Important 2 — đường trích xuất thất bại không có coverage HTTP, và một test mang tên sai che mất điều đó

`test_failed_extraction_is_reported` mang tên đường thất bại nhưng khẳng định điều
ngược lại. `get_llm_provider` **chưa bao giờ** nằm trong `app.dependency_overrides`
ở bất kỳ test nào.

### Important 3 — sàn `anthropic` khai báo không hỗ trợ API mà code gọi

`pyproject.toml` khai `anthropic>=0.40` nhưng code gọi `messages.parse(...)`, chỉ có
từ dòng 1.x. Dưới sàn đó, `AttributeError` bị `except Exception` nuốt và **mọi** báo
cáo âm thầm thành `failed` với thông điệp trông như lỗi API chứ không phải lỗi phụ thuộc.

---

## Xác minh bằng chạy code

- Toàn bộ suite: 122 pass, 1 warning, 4.37s. Không sinh file `.db`.
- Lỗi Critical, end-to-end qua HTTP, đọc lại sổ cái bằng SQL thô.
- Ba triệu chứng của Important 1.
- `date.today()` đúng 1 lần trong `app/`; `HTTPException` 0 lần; `KpiProgressEntry` không có đường UPDATE/DELETE.
- **Độ trung thực của test dưới session dùng chung.** `api_client` và thân test dùng chung một Session với `expire_on_commit=False` — rủi ro đúng đắn lớn nhất của bộ test. Nhân bản cây sang scratchpad, đổi thành `expire_on_commit=True`, **cả 122 vẫn pass** → không test nào xanh nhờ trạng thái cũ trong bộ nhớ.
- **Độ có-thể-đỏ, bằng 11 đột biến.** Chín cái làm suite đỏ: xoá guard trích lại (4 đỏ), xoá cổng validate (3), sổ cái từ `suggested_*` (2), ghi đè `suggested_*` (3), `effective_date` từ today (1), không xoá blocker khi trích lại (1), không ghi `provider_name` (2), xoá luôn dòng rejected (1). Hai sống sót: một là equivalent mutant, một lộ ra dòng chết tại `extraction.py:99`.

## Xác minh bằng đọc

- Mọi `db.add` trong `run_extraction` nằm sau `try/except`, nên thất bại không để lại hàng nào.
- `failed` + có suggestion approved là không tới được qua API.
- Ranh giới giao dịch trong `approval.py` (suite đã có hai test fault-injection).

## Giả định, không kiểm

- Hành vi của `anthropic` 1.5 tại biên mạng (không gọi API thật, theo chỉ thị).
- Sắc thái câu chữ tiếng Việt trong thông điệp lỗi.

---

## Phán quyết về các quyết định của controller

Reviewer **đồng ý với toàn bộ** phán quyết trong ledger. Ba mục được xác nhận riêng:
cột enum phải lưu giá trị chữ thường; hai lần khẳng định dựa vào id là lỗi plan chứ
không phải lỗi implementer; thiếu fault-injection cho đường duyệt task là lỗ hổng plan.

Hai quan sát thay vì bất đồng:

1. Quyết định `exclude_none` (bỏ qua `null` tường minh trong PATCH) là hợp lý và đã tự nêu đánh đổi, nhưng test hiện đã **đóng băng** hành vi "âm thầm bỏ qua" thành hợp đồng. Khi frontend vào, `null` nên thành 422.
2. **Điểm mù mà không phán quyết nào bắt được, vì không ai đặt câu hỏi.** Global Constraints nhấn mạnh `validate_extraction_result` là cổng duy nhất trên output của *mọi provider*, và code tôn trọng điều đó hoàn toàn. Nhưng câu hỏi đối xứng — *cái gì kiểm con số của **quản lý**, tức con số thật sự tới sổ cái* — chưa từng được đặt ở cấp plan, cấp task, hay trong cả mười bốn vòng review. Bất đối xứng đó chính là lỗi Critical ở trên. Đây là lỗ hổng cấp plan, không phải một phán quyết sai.
