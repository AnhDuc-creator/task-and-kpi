# Ghi chú về quy trình làm việc (khung để tự đánh giá)

**Mục đích:** khung để tôi tự chấm quy trình đã chạy trên repo này, không phải một
bản đề xuất quy trình mới.

**Nguồn dữ kiện:** `docs/superpowers/specs/*`, `docs/superpowers/plans/*`,
`docs/superpowers/reviews/*`, `docs/diagrams/*`, và lịch sử git (`afe96f1..b48bb30`).

**Nguyên tắc ghi:** chỉ ghi sự kiện tra được trong repo, kèm nguồn. Mọi phán xét
("có đáng công không") để trống cho tôi điền. Chỗ nào không có dữ kiện trong repo thì
ghi thẳng là không có, không đoán.

---

## Các chặng đã thật sự chạy (bản kiểm kê)

| # | Chặng | Hiện vật trong repo |
|---|---|---|
| 1 | Spec thiết kế | `specs/2026-09-11-kpi-report-ai-design.md` (390 dòng), `specs/2026-09-11-frontend-giai-doan-2-design.md` (207 dòng) |
| 2 | Plan theo task/step | `plans/2026-09-11-backend-giai-doan-1.md` (4540 dòng, 14 task), `plans/2026-09-11-frontend-giai-doan-2.md` (2818 dòng), `plans/2026-09-14-sua-lech-spec.md` (1419 dòng, 9 task) |
| 3 | Self-Review trong chính plan | mục `## Self-Review` cuối mỗi plan (vd `plans/2026-09-14-sua-lech-spec.md:1407`) |
| 4 | Pre-flight scan trước khi thực thi | `reviews/2026-09-11-sdd-ledger.md` — bảng "Cặp task dùng chung file hoặc interface" + bảng "Từng task có tự nhất quán không" |
| 5 | Ruling của controller khi plan sai | 8 dòng `Ruling:` trong ledger |
| 6 | TDD + review từng task (14 task) | 11 dòng `review sach`, 22 dòng `minor (deferred)` trong ledger |
| 7 | Review toàn nhánh cuối cùng | `reviews/2026-09-11-final-whole-branch-review.md` |
| 8 | Fix wave sau review cuối | `reviews/2026-09-11-final-fix-report.md`, commit `1f005fc`, `af566c7`, `92c1c78` |
| 9 | Vẽ sơ đồ để đối chiếu code ↔ spec | `docs/diagrams/*.md` (4 file), commit `2dd4197` |
| 10 | Vòng sửa lệch spec + mở PR | plan `2026-09-14`, commit `61f4207..f37ea3c`, PR #1 (`b48bb30`) |
| 11 | Người dùng đọc PR rồi sửa tiếp | `61d909b`, `c63abf6`, `9def1de`, `f37ea3c` |

---

## 1. Chặng nào đã cứu tôi

Mỗi mục: chặng nào, bắt được gì, dẫn nguồn. Dòng "Tôi đánh giá" để trống.

### 1.1 Review toàn nhánh cuối cùng — bắt lỗi Critical mà 14 vòng review task không thấy

- **Bắt được:** `final_delta` không hữu hạn (`1e400` → `inf`) đi thẳng vào sổ cái
  `kpi_progress_entries`. Hậu quả tái hiện được qua HTTP: KPI ở 0% báo `"completed"`,
  `actual_value: null`, cảnh báo tắt; và **không hoàn tác được qua API** (trích lại → 409,
  duyệt lại → 409, bù `-1e400` ra `nan`).
- **Nguồn:** `reviews/2026-09-11-final-whole-branch-review.md`, mục "Critical" (có khối
  repro nguyên văn request/response).
- **Vì sao đáng chú ý:** cùng file ghi rõ nguyên nhân gốc là **câu hỏi chưa ai đặt** —
  plan/spec/mọi review đều hỏi "cái gì kiểm output của LLM" nhưng không ai hỏi "cái gì kiểm
  con số của *quản lý*", tức con số thật sự vào sổ cái. Reviewer xếp đây là "lỗ hổng cấp plan,
  không phải một phán quyết sai".
- **Tôi đánh giá:** _(để trống)_

### 1.2 Review toàn nhánh — bắt một test mang tên sai đang che một lỗ coverage

- **Bắt được:** `test_failed_extraction_is_reported` mang tên đường thất bại nhưng khẳng định
  điều ngược lại; `get_llm_provider` **chưa bao giờ** nằm trong `app.dependency_overrides` ở
  bất kỳ test nào → đường trích xuất thất bại không có coverage mức HTTP.
- **Nguồn:** cùng file, "Important 2"; bản sửa ở `reviews/2026-09-11-final-fix-report.md`
  (Finding 3: đổi tên test, thêm `test_provider_failure_is_reported_over_http` và
  `test_failed_report_can_be_reextracted_over_http`).
- **Ghi chú dữ kiện:** lỗ này tồn tại qua cả 14 vòng review task trước đó (ledger ghi 11 lần
  "review sach").
- **Tôi đánh giá:** _(để trống)_

### 1.3 Mutation testing trong review cuối — cho bằng chứng bộ test "đỏ được"

- **Làm gì:** reviewer chạy 11 đột biến; 9 làm suite đỏ (xoá guard trích lại → 4 đỏ, xoá cổng
  validate → 3, sổ cái xây từ `suggested_*` → 2, ghi đè `suggested_*` → 3, `effective_date`
  lấy today → 1, ...). 2 sống sót: 1 là *equivalent mutant*, 1 lộ ra dòng chết tại
  `extraction.py:99`.
- **Cộng thêm:** đổi `expire_on_commit=True` trên bản sao, 122 test vẫn pass → không test nào
  xanh nhờ trạng thái cũ trong bộ nhớ.
- **Nguồn:** `reviews/2026-09-11-final-whole-branch-review.md`, mục "Xác minh bằng chạy code".
- **Tôi đánh giá:** _(để trống)_

### 1.4 Review từng task — bắt lỗi enum lưu sai giá trị, bằng reproduction chứ không bằng đọc

- **Bắt được:** `Enum(..., native_enum=False)` lưu **tên** hằng (`"TODO"`) thay vì **giá trị**
  (`"todo"`) mà spec §5 quy định. Reviewer chứng minh bằng raw `INSERT 'todo'` → `LookupError`
  khi đọc qua ORM.
- **Xử lý:** phán quyết là **lỗi plan**, sửa plan (`8c99b47`) thêm helper `_enum_column` dùng
  `values_callable` cho cả 4 cột, kèm test đọc bằng SQL thô.
- **Nguồn:** ledger, khối `Task 3`.
- **Tôi đánh giá:** _(để trống)_

### 1.5 Review từng task — bắt hai lỗ mã trạng thái ở tầng HTTP (Task 11)

- **Bắt được:** (a) `PATCH /api/kpis` lưu được kỳ ngược (`KpiUpdate` không có guard như
  `KpiCreate`) → `compute_elapsed_ratio` trả 1.0 → KPI bị cảnh báo rủi ro oan; (b)
  `POST /api/employees` trùng email → `IntegrityError` không ai bắt → 500 thay vì 409.
- **Nguồn:** ledger, khối `Task 11`; sửa plan ở `e94549b`, fix ở `6c08ae5`.
- **Tôi đánh giá:** _(để trống)_

### 1.6 Implementer báo BLOCKED thay vì tự lách — bắt hai test khẳng định sai (Task 8, Task 12)

- **Bắt được:** test khẳng định `new_ids.isdisjoint(old_ids)`, nhưng SQLite **cấp lại primary
  key** khi bảng bị xoá sạch, nên hàng mới nhận đúng id vừa xoá. Test đang khẳng định một
  *tình cờ của việc cấp id* thay vì hành vi cần chứng minh.
- **Xử lý:** phán quyết **lỗi plan, không phải lỗi implementer**; sửa plan (`23f6ab4`, rồi
  `5ccce02` cho chỗ sót ở Task 12), giữ nguyên implementation.
- **Nguồn:** ledger, khối `Task 8` và `Task 12`.
- **Tôi đánh giá:** _(để trống)_

### 1.7 Vẽ sơ đồ để đối chiếu — biến "spec lệch code" thành danh sách hữu hạn, sửa được

- **Bắt được:** 4 chỗ code lệch spec (3 router CRUD còn chứa nghiệp vụ; thiếu `CheckConstraint`
  trên `kpis`; thiếu `getKpi`; thiếu `tsconfig.node.json`) và 7 chỗ spec lệch code
  (`source_suggestion_id` nullable, `email UNIQUE`, đường JSON hỏng, nguồn ràng buộc
  `final_kpi_id`, cổng `isfinite` thứ hai, `ScriptedProvider`, `DashboardItemOut`).
- **Nguồn:** mục "Chỗ đã đồng bộ" trong `docs/diagrams/class-diagram.md`,
  `component-diagram.md`, `sequence-approve.md`; plan `2026-09-14-sua-lech-spec.md` mục Goal.
- **Tôi đánh giá:** _(để trống)_

### 1.8 Ràng buộc "hành vi HTTP không đổi, 129 test cũ là lưới an toàn"

- **Làm gì:** vòng refactor tách service đặt ràng buộc toàn cục: không endpoint nào được thêm/
  đổi/bỏ, test cũ không được sửa hay xoá, chỉ được thêm test mới; và bước kiểm cuối là
  `Select-String` ba router tìm `db.commit|db.add|db.get|select(|...Error` — kỳ vọng **không
  in ra dòng nào**.
- **Nguồn:** `plans/2026-09-14-sua-lech-spec.md` mục "Global Constraints" và Task 9 Step 5.
- **Tôi đánh giá:** _(để trống)_

---

## 2. Chặng nào tốn công mà ít giá trị

Phần này chỉ liệt kê **dữ kiện về chi phí và về sản lượng**. Kết luận "có đáng không"
để trống — đó là việc tôi tự chấm.

### 2.1 Khối lượng tài liệu đã viết

| Hiện vật | Dòng |
|---|---|
| `plans/2026-09-11-backend-giai-doan-1.md` | 4540 |
| `plans/2026-09-11-frontend-giai-doan-2.md` | 2818 |
| `plans/2026-09-14-sua-lech-spec.md` | 1419 |
| `specs/2026-09-11-kpi-report-ai-design.md` | 390 |
| `specs/2026-09-11-frontend-giai-doan-2-design.md` | 207 |
| 3 file review | 496 |
| 4 file sơ đồ | 561 |
| **Tổng** | **10 431** |

- Plan chứa **code đầy đủ** để dán (vd `plans/2026-09-14-sua-lech-spec.md:296-378` là toàn văn
  `services/kpi.py`), tức cùng một đoạn code tồn tại hai bản: trong plan và trong repo.
- **Tôi đánh giá:** _(để trống)_

### 2.2 22 mục `minor (deferred)` — bao nhiêu trong số đó đã dẫn tới thay đổi?

- Ledger ghi 22 dòng `minor (deferred)`. Ở review cuối, 3 mục lớn được triage và **cả 3 đều
  `carry`** (DeprecationWarning của Starlette; race check-then-insert; N+1 query).
- Tra trong repo hiện tại: các mục này vẫn còn (README có mục "Hạn chế đã biết" ghi lại
  check-then-insert; `sequence-approve.md` ghi lại `db.refresh` thừa).
- **Dữ kiện thiếu:** repo không ghi thời gian bỏ ra cho từng mục minor, nên không tính được
  tỷ lệ công/kết quả. Tôi tự nhớ.
- **Tôi đánh giá:** _(để trống)_

### 2.3 11 lần "review sach" liên tiếp trên 14 task

- 11/14 task kết thúc `review sach — 0 Critical, 0 Important`. 3 task còn lại ra kết quả:
  Task 3 (enum), Task 9 (thiếu fault-injection cho đường duyệt task), Task 11 (2 Important).
- Ngoài ra 2 task (8, 12) không do reviewer bắt mà do **implementer báo BLOCKED**.
- **Tôi đánh giá:** _(để trống)_

### 2.4 Một phần công sức đi vào thứ không quan sát được

- Reviewer xác định đột biến "đảo thứ tự kiểm `completed`/`at_risk`" là **equivalent mutant**:
  hai nhánh loại trừ nhau nên thứ tự không quan sát được; spec lại quy định thứ tự đó "để kết
  quả luôn xác định". Ghi nguyên văn: cách phá hoà này là *không thể test*, chứ không phải
  chưa test.
- **Nguồn:** `reviews/2026-09-11-final-whole-branch-review.md`, "Ghi chú về §6".
- **Tôi đánh giá:** _(để trống)_

### 2.5 Đếm nhầm số test hai lần, phải ra ruling để sửa tài liệu

- `Task 1`: plan ghi "PASS (4 test)", thực tế 3 → ruling sửa plan.
- `Task 11`: plan ghi "thêm 4 test", thực tế 3, và base là 9 chứ không phải 10 → ruling sửa
  (`4685c56`). Ledger ghi: *"Toi dem sai lan thu hai trong phien nay"*.
- **Tôi đánh giá:** _(để trống)_

### 2.6 Task chỉ sửa tài liệu, và sửa xong vẫn còn sai

- Task 7 của plan `2026-09-14` gồm 12 step chỉ để đồng bộ spec + viết lại 4 sơ đồ. Sau khi
  xong vẫn phải sửa thêm 3 commit nữa cho chính các file đó (`717ea54`, `289175e`, `f37ea3c`)
  — xem mục 3.5.
- **Tôi đánh giá:** _(để trống)_

---

## 3. Chỗ agent làm sai mà không cổng nào chặn được

Tiêu chí xếp mục vào đây: lỗi **đi qua trót lọt** mọi cổng đang có tại thời điểm nó sinh ra
(plan self-review, pre-flight scan, TDD, review từng task, bộ test, review toàn nhánh), chỉ lộ
ra ở một chặng muộn hơn — hoặc chưa lộ ra.

### 3.1 `update_kpi` / `update_task` nhận bất kỳ trường nào — lọt qua **tất cả** cổng, chỉ người dùng đọc PR mới bắt

- **Sai ở đâu:** plan viết thẳng `changes: dict[str, Any]` rồi
  `for field, value in changes.items(): setattr(kpi, field, value)`
  (`plans/2026-09-14-sua-lech-spec.md:296-378`). Không có whitelist trường.
- **Đã đi qua:** mục Self-Review của plan (`:1407`, có hẳn phần "Type consistency" đối chiếu
  chữ ký từng service với schema — vẫn không thấy), 7 test TDD viết sẵn trong plan cho
  `services/kpi.py`, toàn bộ suite backend lúc mở PR, và cả vòng review của task đó.
  (Bản sửa `61d909b` thêm đúng 1 test cho mỗi service: `test_service_kpi.py` 7 → 8,
  `test_service_task.py` 7 → 8; tổng hàm test hiện tại trong `backend/tests/`: 149.)
- **Ai bắt:** người dùng, sau khi PR #1 đã mở. Sửa ở `61d909b`: thêm `KpiChanges(TypedDict)` +
  whitelist runtime `set(changes) - KpiChanges.__optional_keys__` → `ValueError`.
- **Ghi chú:** chính comment trong bản sửa nêu lý do TypedDict không đủ: *"dự án không chạy
  mypy nên TypedDict không tự chặn được key lạ"*.
- **Tôi đánh giá:** _(để trống)_

### 3.2 Bất đối xứng "kiểm output LLM nhưng không kiểm input quản lý"

- **Sai ở đâu:** Global Constraints của plan backend nêu `validate_extraction_result` là cổng
  duy nhất áp lên output của **mọi** provider, và code tôn trọng đúng 100%. Nhưng con số thật
  sự vào sổ cái là `final_delta` của quản lý, và không cổng nào kiểm nó.
- **Đã đi qua:** spec, plan, pre-flight scan, 14 vòng review task.
- **Ai bắt:** review toàn nhánh (mục 1.1). Reviewer ghi rõ: *"câu hỏi đối xứng ... chưa từng
  được đặt ở cấp plan, cấp task, hay trong cả mười bốn vòng review"*.
- **Tôi đánh giá:** _(để trống)_

### 3.3 Bản vá của review cuối, tự nó, vẫn chưa đủ — lỗi thứ hai chỉ lộ ra lúc chạy

- **Sai ở đâu:** brief fix chỉ yêu cầu thêm `allow_inf_nan=False`. Làm đúng vậy thì lỗi
  **biến thành một 500 khác**: handler `RequestValidationError` mặc định của FastAPI echo lại
  input và sập khi `json.dumps(..., allow_nan=False)` gặp `inf` — tức chính phản hồi 422 bị sập.
- **Ai bắt:** implementer, lúc chạy thật; phải thêm exception handler riêng trong `main.py`
  (ngoài phạm vi brief) và đã báo lại thay vì làm lặng lẽ.
- **Nguồn:** `reviews/2026-09-11-final-fix-report.md`, mục "Surprise" trong Finding 2 và mục
  "Concerns"; ledger dòng cuối.
- **Tôi đánh giá:** _(để trống)_

### 3.4 Cùng một lỗi plan xuất hiện lại ở task sau, vì không quét lại toàn plan

- **Sai ở đâu:** sau ruling Task 8 (SQLite cấp lại id), controller không quét toàn plan tìm
  cùng mẫu; Task 12 đâm vào đúng lỗi đó. Ledger ghi: *"la thieu sot cua toi — luc sua Task 8
  toi khong quet lai toan plan tim cung mau nen cho nay con sot"*.
- **Ai bắt:** implementer của Task 12 báo BLOCKED (không phải reviewer, không phải cổng nào).
- **Tôi đánh giá:** _(để trống)_

### 3.5 Tài liệu do chính vòng làm việc sinh ra nhưng sai dữ kiện, không cổng nào kiểm

Không có cổng nào đối chiếu số liệu trong `docs/diagrams/*` và README với code. Bốn lần phải
sửa sau:

| Commit | Sai gì |
|---|---|
| `717ea54` | Số dòng `models.py` trong class-diagram lệch sau khi thêm `CheckConstraint` (`models.py:196` → `:204`, `:63` → `:64`) |
| `289175e` | Thiếu hai `CHECK` trong khối `Kpi` của sơ đồ; kiểu gạch đầu dòng không thống nhất |
| `f37ea3c` | Viết "**Năm** module service còn lại" rồi liệt kê đúng **bốn** cái |
| `9def1de` | README nói chỉ cần xoá `kpi.db`, bỏ sót việc SQLite **không có** `ALTER TABLE ADD CONSTRAINT` nên không có đường nâng cấp tại chỗ |

- **Ai bắt:** người dùng đọc lại sau khi merge.
- **Tôi đánh giá:** _(để trống)_

### 3.6 Chính plan nói sai về công cụ, và bước "kiểm" không kiểm được thứ nó tưởng

- **`tsconfig.node.json` không nằm trong bất kỳ lệnh build nào.** Plan Task 6 Step 2 tự khẳng
  định *"`npm run build` chạy `tsc --noEmit`, không phải `tsc -b`, nên `references` không kích
  hoạt"* — tức đã biết file mới không được build đụng tới, nhưng vẫn chỉ kiểm nó bằng **một
  lệnh tay chạy đúng một lần** (Step 4). Sửa ở `c63abf6`: thêm
  `tsc -p tsconfig.node.json --noEmit` vào script `build`.
- **`tsbuildinfo` bị gọi nhầm là rác.** Step 3 ban đầu dặn: nếu thấy `tsconfig.node.tsbuildinfo`
  thì "xoá nó và bỏ `composite: true`" — làm vậy sẽ gãy `references` (TS6306). Sửa ở `9def1de`
  (và `.gitignore` bổ sung ở `e51ed59`).
- **Vị trí chèn đoạn spec ghi sai.** Step 6 dặn chèn "ngay trước đoạn Quy ước mã lỗi", nhưng
  dòng endpoint vừa sửa lại ghi "xem bên dưới" → trỏ sai chỗ. Sửa ở `9def1de`.
- **Ai bắt:** người dùng, sau khi merge. Không cổng nào kiểm tính đúng của bản thân plan sau
  khi plan đã được thực thi.
- **Tôi đánh giá:** _(để trống)_

### 3.7 Frontend: sáu lỗi hành vi lọt qua 25 test Vitest và review từng task

Gộp ở `56cc560` ("6 fix cuối trước khi merge nhánh"), sau khi mọi task frontend đã `review sach`:

- `ReviewPage` xoá nhập của người dùng **kể cả khi duyệt lỗi** → nguy cơ ghi nhầm giá trị AI gợi
  ý cũ vào sổ cái sau khi quản lý đã sửa.
- Lỗi tải danh mục KPI/công việc không hiện ra → nút "Duyệt" bị disable âm thầm, không rõ lý do.
- `EmployeePicker` không nạp lại danh sách khi điều hướng (Layout được React Router giữ mounted).
- Bảng "Báo cáo gần đây" thiếu cột tên nhân viên → trích lại nhầm báo cáo của người khác.
- `run_e2e.py` `taskkill` vô điều kiện tiến trình đang giữ cổng.
- Hai README thiếu bước cài Playwright.

Trước đó, cùng dạng: `63eeacb` (double-click nút "Trích lại" tạo hai request extract song song),
`43286fb` (xoá trắng nhập ở dòng khác; `Number("1e")` → `NaN` → `null` → 422),
`909e08e` (empty-state "Không có vướng mắc nào" hiện ra **trong lúc đang tải**).

- **Tôi đánh giá:** _(để trống)_

### 3.8 `a06ed07` — lỗi do chính script kiểm thử gây ra, chỉ người dùng bắt

- `free_ports()` ném `SystemExit` từ khối `finally`, **ghi đè mã thoát** mà `try` vừa trả về →
  một lần chạy đã PASS biến thành FAIL.
- `playwright` chưa được khai báo dependency ở đâu cả.
- Commit ghi rõ: *"Hai viec nguoi dung duyet truoc khi merge"*.
- **Tôi đánh giá:** _(để trống)_

### 3.9 Còn mở tới hôm nay — đã ghi nhận, chưa cổng nào bắt và chưa sửa

| Mục | Nguồn |
|---|---|
| `services/extraction.py` commit trần ở 3 chỗ (`:101`, `:127`, `:180`), không theo idiom `try/except → rollback → raise` của 4 service còn lại. Đi qua 14 review task + review toàn nhánh + vòng tách service mà không ai nêu; chỉ lộ ra khi vẽ sơ đồ | `docs/diagrams/sequence-submit-report.md` (mục cuối), thêm vào ở `9def1de` |
| `routers/reports.py:29` vẫn tự `db.get(Employee, ...)` và tự ném `NotFoundError` — đúng loại lỗi mà Task 1-3 vừa sửa ở ba router khác | `docs/diagrams/component-diagram.md`, "Còn lại, đã ghi nhận chứ chưa sửa" |
| Check-then-insert: hai request đồng thời → 500 thay vì 409 (`POST /api/employees`, `POST /api/reports`) | `README.md`, "Hạn chế đã biết" |
| `CheckConstraint` chỉ áp cho DB tạo mới (không có migration; SQLite không có `ALTER TABLE ADD CONSTRAINT`) | `README.md`, "Hạn chế đã biết" |
| `db.refresh` thừa sau `commit` khi `expire_on_commit=False`, cố ý giữ để cả tầng service nhất quán | `docs/diagrams/sequence-approve.md` |
| Dòng chết tại `extraction.py:99` (đột biến M9 làm lộ) | `reviews/2026-09-11-final-whole-branch-review.md` |
| `exclude_none` trong PATCH: `null` tường minh bị **âm thầm bỏ qua**, và test đã đóng băng hành vi đó thành hợp đồng; reviewer đề nghị đổi thành 422 khi frontend vào — frontend đã vào, chưa đổi | `reviews/2026-09-11-final-whole-branch-review.md`, "Phán quyết về các quyết định của controller" |

- **Tôi đánh giá:** _(để trống)_

---

## Chỗ không có dữ kiện trong repo (tôi tự điền)

- Thời gian thực tế bỏ ra cho từng chặng — repo chỉ có timestamp commit, không có thời lượng
  đọc/viết/chờ.
- Số lần tôi phải can thiệp bằng tay mà không để lại commit hay dòng ledger.
- Những lần một chặng làm tôi **chậm lại** nhưng không sinh ra hiện vật nào để đếm.
- Mức tin/không tin của tôi vào kết quả ở từng chặng.
