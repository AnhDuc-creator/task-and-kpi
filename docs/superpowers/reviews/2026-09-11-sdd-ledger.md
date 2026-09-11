# SDD ledger — plan: docs/superpowers/plans/2026-09-11-backend-giai-doan-1.md

Spec: docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md (đọc, là thẩm quyền ràng buộc)
Worktree: D:\projects\task-and-kpi\.claude\worktrees\feat-backend-mvp
Branch: worktree-feat-backend-mvp
Base commit: afe96f1

## Pre-flight scan

### Cặp task dùng chung file hoặc interface

| Cặp | Produces → Consumes | Kết quả |
|---|---|---|
| 1 → 6, 12 | `Settings(database_url, llm_provider, anthropic_api_key, anthropic_model)` → factory, dependencies | Khớp |
| 1 → 3, 11 | `Base`, `engine`, `SessionLocal`, `get_db` → conftest, mọi router | Khớp |
| 1 → 11,12,13,14 | `app/main.py` tạo ở T1, mỗi task sau gắn thêm router | Khớp; mỗi task khai báo Modify main.py |
| 2 → 10 | `evaluate_kpi(...) -> KpiEvaluation` → dashboard service | Khớp (7 trường dùng đúng tên) |
| 3 → 7,8,9,10,11,12,13 | 8 model + 3 enum | Khớp |
| 4 → 5, 6, 7 | `ExtractionRequest/Result`, `LlmProvider`, `validate_extraction_result` | Khớp |
| 5 → 7, 8, 9 | `MockProvider`, `ScriptedProvider(result=, error=)` | Khớp |
| 6 → 12 | `get_provider(settings)` → `get_llm_provider()` | Khớp |
| 7 → 8 | `run_extraction`, `build_extraction_request` → `reextract_report` | Khớp (T8 nối vào cuối cùng file) |
| 7 → 9,11,12 | `ConflictError`, `NotFoundError` → service duyệt, exception handler | Khớp |
| 9 → 13 | 4 hàm duyệt, chữ ký keyword-only | Khớp |
| 10 → 14 | `build_dashboard(db, today) -> list[DashboardItem]` | Khớp |
| **3 → 11** | `tests/conftest.py`: T3 tạo `db_session`, T11 nối thêm `api_client` | **XUNG ĐỘT: T11 không khai báo conftest.py trong Files** |
| **11 → 12,13,14** | `app/schemas.py`: T11 viết TOÀN BỘ schema, kể cả của T12–14 | **XUNG ĐỘT: T11 sinh code chưa ai dùng — rubric review coi là defect** |
| **12 → 13** | `tests/test_api_reports.py`: 2 test cần endpoint duyệt của T13 | **XUNG ĐỘT: cuối T12 bộ test đỏ, phải lách bằng `-k`** |

### Từng task có tự nhất quán không

| Task | Kết quả |
|---|---|
| 1 | Nhất quán |
| 2 | Nhất quán (13 test khớp hàm thuần, không chạm DB) |
| 3 | Nhất quán |
| 4 | Nhất quán |
| 5 | Nhất quán |
| 6 | **Test hardcode `"claude-sonnet-5"`, trái Global Constraint "không hardcode tên model"** |
| 7 | Nhất quán |
| 8 | Nhất quán |
| 9 | Nhất quán |
| 10 | Nhất quán |
| 11 | Xem xung đột conftest + schemas ở trên |
| 12 | **`ReportOut.extraction_status: str` nhận enum — serialize không xác định** |
| 13 | Nhất quán |
| 14 | Nhất quán |

## Rulings (pre-flight)

Ruling: T11 chỉ viết schema Employee/Kpi/Task; schema báo cáo → T12, hàng đợi duyệt → T13, dashboard → T14, mỗi task khai báo `Modify: app/schemas.py` — vì plan bắt T11 sinh 9 model chưa endpoint nào gọi, đúng thứ rubric review coi là defect, và tôi không được phép dặn reviewer bỏ qua. Nếu sai: schemas.py bị sửa 4 lần thay vì 1, tốn thêm vài phút mỗi task, không ảnh hưởng code cuối.

Ruling: hai test cần endpoint duyệt chuyển từ T12 sang T13 (`test_reextract_blocked_after_approval_returns_409` được T13 nối vào cuối `test_api_reports.py`; test còn lại thay bằng một test trích xuất rỗng đứng độc lập), bỏ bộ lọc `-k` — vì bộ test phải xanh ở MỌI ranh giới task, nếu không reviewer của T12 đúng khi báo lỗi. Nếu sai: một test nằm ở file hơi lệch chủ đề, dễ chuyển lại sau.

Ruling: T11 khai báo thêm `Modify: backend/tests/conftest.py` — vì Step 1 của nó sửa file do T3 tạo mà khối Files không nói, khiến review package trông như sửa lén. Nếu sai: không có rủi ro, chỉ là khai báo chính xác hơn.

Ruling: `ReportOut.extraction_status` đổi từ `str` sang `ExtractionStatus`, và giữ `SuggestionStatus` cho `status` — vì trường `str` nhận một `str`-Enum thì cách serialize phụ thuộc chi tiết Pydantic, trong khi test khẳng định đúng chuỗi `"extracted"`. Nếu sai: không có; kiểu enum chặt hơn và vẫn ra đúng chuỗi.

Ruling: Global Constraint về hardcode model nới lại thành "code ứng dụng không hardcode; `config.py`, `.env.example` và test khẳng định giá trị mặc định thì được" — vì bản cũ tự mâu thuẫn với test của T6 do chính plan quy định. Nếu sai: reviewer có thể bỏ qua một chỗ hardcode thật trong test, rủi ro thấp vì code ứng dụng vẫn bị cấm.

## Tiến độ

Task 1: BASE 0cd1cce, implementer sonnet -> d07e328, DONE_WITH_CONCERNS (3/3 pass)
Task 1: Ruling: sua plan Step 10 tu "PASS (4 test)" thanh "PASS (3 test)" — implementer dung, code test trong brief chi dinh nghia 3 test (config x2, health x1); loi dem cua toi khi viet plan. Neu sai: khong co, chi la con so ky vong trong tai lieu.
Task 1: quan sat — output test co mot DeprecationWarning tu starlette/anyio (thu vien thu ba, khong phai code cua ta). De reviewer danh gia, khong tu xu ly truoc.
Task 1: review sach — spec OK, quality Approved, 0 Critical, 0 Important.
Task 1: warning-item resolved — db.py chua duoc test nao cham trong diff nay, nhung T3 dung Base, T11 ghi de get_db, moi router phu thuoc get_db. Khong phai lo hong.
Task 1: minor (deferred): DeprecationWarning tu anyio/starlette lam output test khong sach. Fix de xuat: pin starlette/anyio hoac them filterwarnings vao pyproject. LUU Y: se lap lai o moi review sau — final review can triage som.
Task 1: minor (deferred): db.py dung connect_args check_same_thread (rieng SQLite). Dung theo brief; chi la ghi chu cho tuong lai neu doi sang Postgres.
Task 1: complete (commits 0cd1cce..d07e328, review clean)
Task 2: BASE e4126cc, implementer haiku -> 0348968, DONE (16/16 pass, output pristine)
Task 2: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer tu tinh tay 13/13 assertion, xac nhan bien nguong dung.
Task 2: warning-item resolved — "1 warning" trong full suite chinh la DeprecationWarning anyio/starlette tu test_health.py cua Task 1, da ghi nhan. Khong do Task 2 sinh ra.
Task 2: minor (deferred): chua co test cho period_end < period_start (code coi nhu ky dai 0). Duoc chan o tang tren: KpiCreate validator va rang buoc model deu bat period_end >= period_start.
Task 2: complete (commits e4126cc..0348968, review clean)
Task 3: BASE 0348968, implementer sonnet -> 180f958, DONE (21/21 pass)
Task 3: review -> spec OK nhung 1 Important (plan-mandated): Enum(..., native_enum=False) luu TEN hang ("TODO") thay vi GIA TRI ("todo") ma spec quy dinh. Reviewer chung minh bang reproduction: raw INSERT 'todo' -> LookupError khi doc qua ORM.
Task 3: Ruling: phat hien THANG plan. Spec muc 5 ghi ro ENUM(todo, doing, done) la tu vung luu tru, nen code phai doi. Sua plan (8c99b47): them helper _enum_column co values_callable, dung cho ca 4 cot enum, va them test doc bang SQL tho de loi nay khong quay lai im lang. Neu sai: cot enum luu chu thuong thay vi chu hoa — khong the hong gi, vi chua co du lieu nao ton tai.
Task 3: warning-item resolved — spec liet ke "period_end >= period_start" va "target_value > 0" duoi bang kpis nhung khong noi o tang nao; plan dat o Pydantic (KpiCreate: Field(gt=0) + model_validator), Task 11 co test khang dinh 422. Chap nhan cho MVP; insert thang vao DB van lach duoc (chi test moi lam vay).
Task 3: fix round 1/5 dang chay — FIX_BASE 8c99b47
Task 3: fix round 1/5 (1 addressed, 0 open; commits 8c99b47..c8c0c85) — ca 4 cot enum qua helper, test raw-SQL co rang.
Task 3: minor (deferred): test raw-SQL chi kiem 2/4 cot (tasks.status, weekly_reports.extraction_status); hai cot suggestion dung y het mot code path nen rui ro thap.
Task 3: complete (commits 0348968..c8c0c85, review clean sau 1 fix round)
Task 4: BASE c8c0c85, implementer sonnet -> 0af440f, DONE (32/32 pass)
Task 4: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer di het 3 truong id + duong finiteness, khong tim thay lo hong.
Task 4: warning-item resolved — viec noi validate_extraction_result vao service la Task 7 (plan muc 7.2), dung pham vi.
Task 4: minor (deferred): 3 vong lap kiem id lap lai cung hinh dang; co the gom bang helper _check_id. Thuan tham my.
Task 4: minor (deferred): docstring ExtractionError nhac "JSON hong, sai schema" ma module nay khong tu phat hien; Task 6 (provider) va Task 7 (service bat ValidationError) moi dung den. Kiem lai o final review.
Task 4: complete (commits c8c0c85..0af440f, review clean)
Task 5: BASE 0af440f, implementer haiku -> 5a18212, DONE (40/40 pass)
Task 5: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer hand-trace 8/8 test.
Task 5: warning-item resolved — factory doc LLM_PROVIDER la Task 6, dung pham vi.
Task 5: minor (deferred): keyword "chan " co dau cach cuoi nen bo lot "bi chan." (dinh dau cau), trong khi ban co dau "chan" khong bi. Bat doi xung nho trong heuristic cua test double.
Task 5: minor (deferred): ScriptedProvider dung duoc voi ca result lan error deu None, chi ném ValueError luc extract() chu khong luc khoi tao. Khong co test phu.
Task 5: complete (commits 0af440f..5a18212, review clean)
Task 6: BASE 5a18212, implementer sonnet -> f41ac45, DONE (50/50 pass). anthropic 1.5.0 cai dat, co messages.parse(output_format=) — client gia khop SDK that.
Task 6: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer tu doc source anthropic 1.5.0 trong .venv de kiem chung thay vi tin bao cao: messages.parse(output_format=) co that, "refusal" la StopReason hop le, parsed_output la property tra None khi khong khop. Xac nhan them: schema validation chay dong bo trong .parse() nen response sai schema cung thanh ExtractionError.
Task 6: warning-item resolved — noi gate vao service la Task 7.
Task 6: minor (deferred): build_user_prompt(request) goi ben trong khoi try nen loi dung prompt cung bi boc thanh "Goi Anthropic that bai", gay nham khi debug. Nen hoist ra ngoai try.
Task 6: minor (deferred): FakeResponse mo phong parsed_output bang thuoc tinh phang, khong dien lai duong property cua SDK that. Reviewer da doc source de bu.
Task 6: complete (commits 5a18212..f41ac45, review clean)
Task 7: BASE f41ac45, implementer sonnet -> 23f66df, DONE (61/61 pass)
Task 7: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer xac nhan moi db.add nam SAU khoi try/except nen that bai khong de lai hang nao; ConflictError nem truoc khi chen; khong exception nao khac thoat duoc run_extraction.
Task 7: warning-item resolved — anh xa ConflictError -> 409 la Task 11.
Task 7: minor (deferred): submit_report dung SELECT-then-INSERT, khong bat IntegrityError. Khi nop dong thoi cung (employee_id, week_start), backstop DB ném IntegrityError chu khong phai ConflictError -> se thanh 500 thay vi 409. Race hiem o MVP mot nguoi dung.
Task 7: minor -> CARRY vao Task 8: rows moi them qua FK tho (report_id=report.id), khong qua report.kpi_suggestions.append(), nen collection da nap san se cu. run_extraction ket thuc bang db.refresh(report) nen duoc giai quyet; Task 8 phai giu buoc refresh do.
Task 7: complete (commits f41ac45..23f66df, review clean)
Task 8: implementer sonnet bao BLOCKED — 2/8 test cua brief fail tren chinh code cua brief. Root cause: SQLite cap lai primary key khi bang bi xoa sach, nen hang moi nhan dung id vua xoa; assert new_ids.isdisjoint(old_ids) sai.
Task 8: Ruling: LOI PLAN, khong phai loi implementer. Hai test do khang dinh mot tinh co cua viec cap id thay vi hanh vi can chung minh. Sua plan (23f6ab4): danh dau noi dung dong cu ("DAU VET CU") roi khang dinh dong con lai khong mang dau do. Implementation cua reextract_report giu nguyen. Neu sai: test van chung minh dung viec thay the, chi doi cach do; rui ro thap.
Task 8: implementer duoc noi lai voi brief da regenerate; kem yeu cau tu tham dinh test moi con co the fail duoc khong.
Task 8: sau ruling -> 83b1894, DONE (69/69 pass). Implementer tu mutation-test 2 test viet lai (vo hieu hoa vong xoa) de chung minh chung van do duoc, roi khoi phuc.
Task 8: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer xac nhan: dieu kien cho phep khop luat (De Morgan), quet ca 2 bang, duong bi chan tro that (raise la lenh dau tien), submit_report/run_extraction khong bi sua, va CA HAI test viet lai deu falsifiable.
Task 8: minor (deferred): test_blocked_reextraction_changes_nothing chua khang dinh them extraction_status/extraction_error va id task-suggestion khong doi.
Task 8: minor (deferred): _has_approved_suggestion dung 2 SELECT rieng thay vi 1 truy van gop. Hop ly o quy mo nay.
Task 8: complete (commits 23f66df..83b1894, review clean sau 1 ruling plan-defect)
Task 9: BASE 83b1894, implementer sonnet -> 6ee9596, DONE (82/82 pass)
Task 9: review -> spec OK nhung 1 Important (plan-inherited): khong co test fault-injection cho approve_task_suggestion, du spec ghi ro duong task cung phai nguyen tu. Reviewer tu viet bien the split-commit de chung minh test rollback duong KPI CO phan biet duoc.
Task 9: Ruling: phat hien THANG plan. Spec muc 7.4 ghi ro "viec doi status cua suggestion va cap nhat tasks cung nam trong mot giao dich duy nhat" — thieu test la thieu bang chung. Sua plan (83e9ecd): them test cho hong o lan goi _utcnow() THU HAI, khi ca suggestion lan task deu da bi sua, nen rollback phai hoan ca hai. Code approval.py giu nguyen. Neu sai: them mot test, khong doi hanh vi.
Task 9: minor (deferred): final_kpi_id/final_task_id "bat buoc non-null" chi duoc dam bao gian tiep qua db.get(Model, None) tra None; SQLAlchemy canh bao hanh vi nay co the doi. Tang HTTP (Task 11, Pydantic int) chan truoc nen khong voi toi duoc qua API.
Task 9: minor (deferred): _utcnow() trong approval.py trung voi helper cung ten trong models.py.
Task 9: warning-item — chua co test nao dat final_kpi_id KHAC suggested_kpi_id (ca duong "LLM tra null, quan ly gan tay"). Kiem o Task 13 (router co body final_kpi_id) va final review.
Task 9: fix round 1/5 dang chay — FIX_BASE 83e9ecd
Task 9: fix round 1/5 (1 addressed, 0 open; commits 83e9ecd..132a2ec) — test-only, approval.py khong doi, test phan biet duoc split-commit.
Task 9: complete (commits 83b1894..132a2ec, review clean sau 1 fix round)
Task 10: BASE 132a2ec, implementer haiku -> e119b96, DONE (89/89 pass)
Task 10: review sach — spec OK, quality Approved, 0 Critical, 0 Important.
Task 10: minor (deferred): N+1 query o kpi.owner.name (lazy relationship, 1 SELECT moi KPI). Khong phai loi dung dan o quy mo MVP; can selectinload neu so KPI tang.
Task 10: minor (deferred): build_dashboard thieu docstring trong khi current_values co.
Task 10: complete (commits 132a2ec..e119b96, review clean)
Task 11: BASE e119b96, implementer sonnet -> 6937aa6, DONE (98/98 pass). Controller xac nhan: khong co file .db nao sinh ra khi chay test (lifespan hoat dong dung).
Task 11: controller housekeeping e7c2db6 — them *.egg-info/ vao .gitignore (artifact cua pip install -e, khong task nao so huu).
Task 11: review -> spec OK nhung 2 Important (plan-mandated):
  (a) PATCH /api/kpis luu duoc ky nguoc (KpiUpdate khong co guard nhu KpiCreate). Hau qua: compute_elapsed_ratio tra 1.0 -> KPI bi canh bao rui ro oan.
  (b) POST /api/employees trung email -> IntegrityError khong ai bat -> 500, trong khi spec quy dinh 409 cho xung dot trang thai.
  + 1 Minor cung goc: null tuong minh trong PATCH -> 500.
Task 11: Ruling: ca hai phat hien THANG plan. Spec muc 9 quy dinh ky luat 404/409/422 va muc 5 quy dinh period_end >= period_start. Sua plan (e94549b): them InvalidInputError -> 422; kiem ky sau khi tron voi du lieu dang luu (vi PATCH mot moc van dao duoc ky); kiem email truoc khi chen -> 409; exclude_none cho ca hai router PATCH; them 4 test. Neu sai: exclude_none bo qua null tuong minh thay vi tra 422 — chon "bo qua" cho MVP frontend tin cay; de doi lai thi la mot dong.
Task 11: fix round 1/5 dang chay — FIX_BASE e94549b
Task 11: fix -> 6c08ae5 (101/101 pass). Implementer tu go db.rollback() ra de xac nhan dong do gach viec, roi khoi phuc. Dong y voi exclude_none cho MVP, co luu y cho giai doan 2.
Task 11: Ruling: sua so test ky vong tu 14 thanh 13 (4685c56). Toi dem sai lan thu hai trong phien nay (Task 1 cung vay) — plan noi "them 4 test" nhung thuc te chi them 3, va base la 9 chu khong phai 10. Neu sai: khong co, chi la con so trong tai lieu.
Task 11: fix round 1/5 (3 addressed, 0 open; commits e94549b..6c08ae5). Re-reviewer tu chung minh rollback gach viec qua cau hinh session (autoflush=False + identity map), khong chi tin bao cao.
Task 11: minor (deferred): kiem email la check-then-insert nen van con race that su (hai request cung qua check truoc khi ai commit) -> IntegrityError -> 500. Chap nhan o MVP mot tien trinh.
Task 11: complete (commits e119b96..6c08ae5, review clean sau 1 fix round)
Task 12: implementer sonnet bao BLOCKED — test_reextract_replaces_pending_suggestions fail vi assert new_id != old_id, CUNG MAU LOI da phan quyet o Task 8. Implementer tai hien duoc ben ngoai FastAPI de chung minh khong phai loi router cua no.
Task 12: Ruling: LOI PLAN, va la thieu sot cua toi — luc sua Task 8 toi khong quet lai toan plan tim cung mau nen cho nay con sot. Da quet lai toan bo (grep old_id/new_id/isdisjoint): khong con cho nao khac. Sua plan (5ccce02): danh dau evidence dong cu qua db_session (api_client dung chung session) roi khang dinh dong con lai khong mang dau. Neu sai: test van chung minh dung viec thay the, chi doi cach do.
Task 12: sau ruling -> 8c17bde, DONE (107/107 pass). Implementer tu kiem test viet lai van do duoc (vo hieu hoa vong xoa -> assert 2 == 1), khong cham mang, khong sinh file .db.
Task 12: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer chay kiem chung that: str(ExtractionStatus.EXTRACTED) cho "ExtractionStatus.EXTRACTED", chung minh vi sao truong phai khai kieu enum. Xac nhan khong assertion nao xanh nho trang thai cu trong bo nho.
Task 12: minor (deferred): get_report va reextract lap lai khoi "lay report hoac 404"; co the gom thanh helper.
Task 12: complete (commits 4685c56..8c17bde, review clean sau 1 ruling plan-defect)
Task 13: Ruling: dong muc treo tu Task 9 — them test duyet de xuat vao mot KPI KHAC voi KPI LLM doan (6c6371a), khang dinh so cai ghi vao KPI quan ly chon va suggested_kpi_id con nguyen. Day la co che "LLM tra null, quan ly gan tay" ma thiet ke dua vao nhung chua co bang chung. Neu sai: them mot test, khong doi hanh vi.
Task 13: BASE 8c17bde (fix base 6c6371a), implementer sonnet dang chay
Task 13: implementer sonnet -> d9c23a2, DONE (118/118 pass)
Task 13: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer xac nhan test gan-lai-KPI la bang chung that (doc hang KpiProgressEntry da commit, se do neu so cai xay tu suggested_kpi_id). Muc treo tu Task 9 DA DONG.
Task 13: minor (deferred): row.report.employee.name gay lazy-load moi hang (N+1) o hang doi duyet. On o quy mo MVP.
Task 13: complete (commits 8c17bde..d9c23a2, review clean)
Task 14: BASE d9c23a2, implementer sonnet -> 9068de5, DONE (122/122 pass, 0 skip)
Task 14: implementer luu y (chua phan loai): dashboard khong co phan trang; duong AnthropicProvider khong duoc chay trong e2e HTTP, chi unit-test (du kien, do rang buoc khong mang).
Task 14: review sach — spec OK, quality Approved, 0 Critical, 0 Important. Reviewer xac nhan: date.today() xuat hien DUNG MOT LAN trong app/ (router dashboard), e2e khong mong manh theo ngay, va khong the xanh neu dashboard doc tong cache.
Task 14: minor (deferred): dashboard khong phan trang (dung pham vi MVP).
Task 14: minor (deferred): AnthropicProvider khong duoc di qua vong HTTP e2e, chi unit-test — du kien do rang buoc khong mang.
Task 14: complete (commits d9c23a2..9068de5, review clean)

== TAT CA 14 TASK HOAN TAT — 122 test pass, 0 skip ==

== FINAL WHOLE-BRANCH REVIEW (opus) — verdict: Merge after fixes ==
FINAL-Critical: final_delta khong huu han (1e400 -> inf) di thang vao so cai. KPI 0% bao la "completed", canh bao tat, khong sua duoc qua API (bao cao da khoa 409, bu -1e400 ra nan). Nguyen nhan goc: plan/spec/moi review deu hoi "cai gi kiem output cua LLM" nhung KHONG AI hoi "cai gi kiem con so cua QUAN LY" — con so that su vao so cai.
FINAL-Important-1: cung lo do, NaN/1e400 o POST /api/kpis va approve tra 500 hoac 201 thay vi 422.
FINAL-Important-2: duong trich xuat that bai khong co coverage HTTP; get_llm_provider chua bao gio duoc override; mot test mang ten sai che mat lo hong.
FINAL-Important-3: pyproject khai anthropic>=0.40 nhung code goi messages.parse (chi co tu 1.x) -> moi bao cao am tham thanh failed.
FINAL: reviewer chay 11 mutation, 9 lam suite do (chung minh test co rang); 2 song sot: M4 la equivalent mutant (thu tu completed/at_risk khong quan sat duoc), M9 lo ra dong chet extraction.py:99.
FINAL: reviewer doi expire_on_commit=True tren ban sao va 122 test VAN PASS -> khong test nao xanh nho trang thai cu trong bo nho.
FINAL: reviewer dong y voi TAT CA rulings trong ledger. Nang T14-b thanh mot phan cua Important-2.
FINAL: triage 3 muc deferred lon: DeprecationWarning -> carry (loi Starlette, khong phai code ta); race check-then-insert -> carry (MVP mot tien trinh); N+1 -> carry (khong anh huong dung dan).
FINAL fix wave dang chay — BASE 9068de5
FINAL fix wave -> 1f005fc, af566c7, 92c1c78 (129/129 pass). Repro Critical chay lai: 1e400 va NaN deu tra 422, so cai 0 hang, suggestion van pending.
FINAL fix: implementer phat hien them — chi them allow_inf_nan=False thi loi bien thanh 500 KHAC, vi handler RequestValidationError mac dinh cua FastAPI echo lai input va sap khi serialize inf. Phai them validation-error handler rieng trong main.py (ngoai brief). Da bao lai, khong lam lang le.
