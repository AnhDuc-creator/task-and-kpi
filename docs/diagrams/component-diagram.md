# Sơ đồ thành phần — frontend ↔ API ↔ services ↔ rules/llm ↔ SQLite

Nguồn sự thật: `frontend/src/` (App.tsx, api.ts, pages/, lib/, context/), `backend/app/main.py`,
`backend/app/routers/`, `backend/app/services/`, `backend/app/rules.py`, `backend/app/llm/`,
`backend/app/models.py`, `backend/app/db.py`, `backend/app/config.py`.

```mermaid
flowchart LR

    subgraph BROWSER["Trình duyệt — http://localhost:5173 (Vite, strictPort)"]
        direction TB
        subgraph SHELL["App shell"]
            LAYOUT["Layout.tsx + EmployeePicker.tsx<br/>4 NavLink"]
            CTX["context/CurrentEmployee.tsx<br/>currentEmployeeId → localStorage"]
        end
        subgraph PAGES["4 trang — React Router"]
            SETUP["SetupPage.tsx<br/>/setup"]
            REPORT["ReportPage.tsx<br/>/report"]
            REVIEW["ReviewPage.tsx<br/>/review"]
            DASHP["DashboardPage.tsx<br/>/dashboard"]
        end
        HOOK["lib/useAsync.ts<br/>không cache, reload = gọi lại mạng"]
        FMT["lib/format.ts<br/>detailToMessage, barGeometry,<br/>mondayOf, formatPercent"]
        APICLIENT["api.ts<br/>fetch thuần + ApiError status, detail<br/>API_BASE = VITE_API_BASE ?? 127.0.0.1:8000"]
    end

    subgraph BACKEND["backend/ — FastAPI + Uvicorn, cổng 8000"]
        direction TB
        MAIN["main.py<br/>CORS chỉ cho http://localhost:5173<br/>handler: 404 / 409 / 422<br/>GET /api/health"]

        subgraph ROUTERS["routers/ — biên HTTP"]
            R_EMP["employees.py"]
            R_KPI["kpis.py"]
            R_TASK["tasks.py"]
            R_REP["reports.py"]
            R_SUG["suggestions.py"]
            R_DASH["dashboard.py<br/>đọc date.today ở đây"]
        end

        DEPS["dependencies.py + config.py<br/>get_llm_provider, Settings từ .env"]

        subgraph SERVICES["services/ — nghiệp vụ, ranh giới giao dịch"]
            S_EXT["extraction.py<br/>submit_report, run_extraction,<br/>reextract_report"]
            S_APP["approval.py<br/>approve/reject kpi và task"]
            S_DASH["dashboard.py<br/>current_values, build_dashboard"]
            S_EMP["employee.py<br/>list, create + kiểm email trùng"]
            S_KPI["kpi.py<br/>list, get, create, update<br/>+ kiểm kỳ ngược sau khi trộn PATCH"]
            S_TASK["task.py<br/>list, create, update"]
        end

        RULES["rules.py — hàm thuần<br/>evaluate_kpi, compute_elapsed_ratio<br/>RISK_THRESHOLD = 0.8<br/>không chạm DB, today qua tham số"]

        subgraph LLM["llm/ — chỉ Pydantic vào ra, không biết SQLAlchemy"]
            L_BASE["base.py<br/>LlmProvider Protocol<br/>ExtractionRequest / ExtractionResult<br/>validate_extraction_result"]
            L_FACT["factory.py<br/>LLM_PROVIDER = mock hoặc anthropic"]
            L_MOCK["mock.py<br/>MockProvider mặc định<br/>+ ScriptedProvider cho test"]
            L_ANT["anthropic_provider.py<br/>messages.parse, output_format"]
            L_PROMPT["prompt.py<br/>SYSTEM_PROMPT, build_user_prompt"]
        end

        DATA["models.py + db.py<br/>8 bảng, Base.metadata.create_all<br/>SessionLocal, get_db"]
        SCHEMAS["schemas.py<br/>Pydantic cho HTTP"]
    end

    SQLITE[("SQLite<br/>DATABASE_URL<br/>mặc định sqlite:///./kpi.db")]
    CLAUDE["Anthropic API<br/>claude-sonnet-5"]

    LAYOUT --> SETUP & REPORT & REVIEW & DASHP
    CTX -.-> LAYOUT
    CTX -.-> REPORT
    PAGES --> HOOK
    PAGES --> FMT
    HOOK --> APICLIENT
    APICLIENT --> FMT

    SETUP -->|"employees, kpis, tasks"| APICLIENT
    REPORT -->|"reports, extract"| APICLIENT
    REVIEW -->|"suggestions"| APICLIENT
    DASHP -->|"dashboard + reports lấy blockers"| APICLIENT

    APICLIENT ==>|"HTTP/JSON, CORS"| MAIN

    MAIN --> ROUTERS
    ROUTERS <--> SCHEMAS
    R_REP --> DEPS
    DEPS --> L_FACT

    R_REP --> S_EXT
    R_SUG --> S_APP
    R_DASH --> S_DASH

    S_DASH --> RULES
    S_EXT --> L_BASE
    L_FACT --> L_MOCK
    L_FACT --> L_ANT
    L_ANT --> L_PROMPT
    L_MOCK -.->|"implements"| L_BASE
    L_ANT -.->|"implements"| L_BASE
    L_ANT -->|"HTTPS"| CLAUDE

    S_EXT --> DATA
    S_APP --> DATA
    S_DASH --> DATA
    S_EMP --> DATA
    S_KPI --> DATA
    S_TASK --> DATA
    DATA --> SQLITE

    R_EMP --> S_EMP
    R_KPI --> S_KPI
    R_TASK --> S_TASK
```

## Giải thích

- **Bốn trang, một tầng API duy nhất.** Mọi trang đều đi qua `useAsync` → `api.ts`; không có
  state manager và không có cache, nên sau mỗi lần ghi chỉ cần `reload()` là số trên màn hình đúng.
  State toàn cục duy nhất là `currentEmployeeId` trong context, lưu ở `localStorage`.
- **CORS chốt origin, không chốt host đích.** `main.py` chỉ cho phép `http://localhost:5173`,
  trong khi `api.ts` gọi sang `http://127.0.0.1:8000` — hợp lệ, vì CORS xét origin của *trang*.
  Đó cũng là lý do `vite.config.ts` đặt `strictPort: true`: nhảy sang 5174 là trượt CORS.
- **Ba tầng phía sau router.** `services/` giữ nghiệp vụ và mở/đóng giao dịch; `rules.py` là hàm
  thuần (không DB, "hôm nay" truyền qua tham số — `routers/dashboard.py` là nơi duy nhất gọi
  `date.today()`); `llm/` chỉ nhận và trả Pydantic.
- **Provider chọn lúc chạy.** `dependencies.get_llm_provider` → `factory.get_provider(settings)`
  đọc `LLM_PROVIDER` từ `.env`, mặc định `mock`, nên toàn bộ test chạy được mà không cần mạng.
  `validate_extraction_result` trong `base.py` được `services/extraction.py` gọi sau **mọi** provider.
- **Một nguồn số liệu duy nhất.** `services/dashboard.py` cộng `kpi_progress_entries` mỗi lần đọc;
  không có cột `current_value` trên `kpis`.

## Chỗ đã đồng bộ

1. **Ba router CRUD giờ đã có service.** Spec §4 quy định "`routers` chỉ dịch HTTP ↔ service,
   không chứa quyết định nghiệp vụ". `routers/employees.py`, `routers/kpis.py`,
   `routers/tasks.py` trước đây tự `db.add` / `setattr` / `db.commit` và tự chứa nghiệp vụ.
   **Đã sửa code theo spec:** `services/employee.py`, `services/kpi.py`, `services/task.py`
   nhận toàn bộ quyết định (email trùng, kỳ ngược, khoá ngoại có tồn tại không) và cả
   ranh giới giao dịch. Ba router chỉ còn gọi service và trả kết quả — hành vi HTTP không đổi.
2. **`frontend/src/api.ts` đã có `getKpi`.** Khớp đủ danh sách hàm mà spec frontend §6 liệt kê.
   Không trang nào gọi nó: `ReviewPage` đã nạp cả danh sách KPI cho dropdown, `updateKpi`
   đã trả về KPI mới. `api.ts` khớp 1-1 với danh sách endpoint §9 là hợp đồng của tầng API,
   và `lib/api.test.ts` là nơi gọi thật.
3. **`frontend/tsconfig.node.json` đã tồn tại**, phủ `vite.config.ts` — file mà
   `"include": ["src"]` của `tsconfig.json` bỏ sót.
4. **`ScriptedProvider` là một lớp riêng.** **Đã sửa spec theo code:** §8 giờ liệt kê nó
   tách khỏi `MockProvider` kèm lý do.
5. **`GET /api/dashboard` trả tập cha.** **Đã sửa spec theo code:** §9 giờ liệt kê đủ
   `DashboardItemOut`.

## Còn lại, đã ghi nhận chứ chưa sửa

- `routers/reports.py:29` vẫn tự kiểm `db.get(Employee, ...)` và tự ném `NotFoundError`.
  Cùng loại với ba chỗ trên nhưng nằm trên đường trích xuất, nên để riêng ra ngoài
  phạm vi lần này.
