# Frontend (Giai đoạn 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng frontend React + Vite + TypeScript với bốn trang (Thiết lập, Nộp báo cáo, Hàng đợi duyệt, Dashboard) trên backend đã hoàn thành, và chứng minh trọn vòng chạy được trên trình duyệt thật.

**Architecture:** Mỗi trang tự nạp dữ liệu qua hook `useAsync` dùng chung; không có cache toàn cục, nên không có bug cache cũ. Trạng thái dùng chung duy nhất là `currentEmployeeId` (React context + `localStorage`). `api.ts` là lớp mỏng bọc `fetch`, chuẩn hoá mọi lỗi thành `ApiError { status, detail }` ngay tại biên. Toàn bộ logic thuần nằm trong `lib/format.ts` — đó là bề mặt Vitest bám vào; UI thật do một kịch bản Playwright trọn vòng kiểm.

**Tech Stack:** React 18, Vite 5, TypeScript 5 (strict), React Router 6, Vitest 2, Playwright (Python, chạy bằng `.venv` ở thư mục gốc repo).

**Spec:** `docs/superpowers/specs/2026-09-11-frontend-giai-doan-2-design.md` (và spec gốc `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md` §9–§10)

## Global Constraints

- **Không sửa bất kỳ file nào trong `backend/`.** Backend đang có 129 test pass. Nếu gặp tình huống bắt buộc phải sửa, **dừng lại và báo người dùng**, kèm lý do cụ thể; không tự ý sửa.
- Tên biến, hàm, component, file: **tiếng Anh**. Chữ hiển thị cho người dùng và comment giải thích: **tiếng Việt**.
- Frontend chỉ được mở qua `http://localhost:5173`. **Không dùng `127.0.0.1:5173`** — backend chỉ mở CORS cho đúng origin `http://localhost:5173` (`backend/app/main.py:29`), và `127.0.0.1` là một origin khác.
- `vite.config.ts` phải đặt `strictPort: true`. Nếu 5173 bị chiếm, Vite phải báo lỗi chứ không được nhảy sang 5174 — cổng 5174 sẽ trượt CORS và tạo ra lỗi rất khó lần.
- `API_BASE` mặc định là `http://127.0.0.1:8000` (host đích không ảnh hưởng CORS; chỉ origin của trang mới ảnh hưởng).
- `percent_complete` do backend trả về là **phân số**, không phải số phần trăm. Mọi chỗ hiển thị phải nhân 100. Bằng chứng, không phải suy đoán: `backend/app/rules.py:70` tính `percent_complete = actual_value / target_value`, và test backend khẳng định thang này — `backend/tests/test_rules.py:90` chốt `actual=100, target=100 → 1.0`, `test_rules.py:101` chốt `actual=120, target=100 → 1.2` (không kẹp trên 1). Nói cách khác `1.0` nghĩa là 100%.
- Frontend chạy trên Windows. `scripts/with_server.py` spawn server bằng `shell=True`, nên lệnh được đưa qua `cmd.exe /c` và `npm` tự phân giải thành `npm.cmd` — **không** cần gọi `npm.cmd` tường minh, và **không** được sửa `with_server.py` vì lý do này. Lệnh đổi thư mục phải là `cd /d` (có `/d`) để chuyển được cả ổ đĩa.
- Phần trăm **hiển thị** không kẹp trên 100 (spec gốc §6 quy định rõ). Chỉ hình học thanh tiến độ mới kẹp trong 0–100.
- `final_kpi_id` và `final_task_id` bắt buộc khác `null` khi duyệt (spec gốc §7.4) → nút Duyệt phải bị vô hiệu khi người dùng chưa chọn.
- Không thêm react-query hay bất kỳ state manager nào (spec gốc §10).
- Không có nút xoá Employee / KPI / Task — backend không có endpoint DELETE.
- Mọi lệnh `npm` chạy từ thư mục `frontend/`. Mọi lệnh Python chạy bằng `.venv` ở **thư mục gốc repo**, không phải venv riêng.
- Mỗi task kết thúc bằng một commit.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `frontend/package.json` | Dependency và script (`dev`, `build`, `test`) |
| `frontend/vite.config.ts` | Cấu hình Vite + Vitest, ghim cổng 5173 |
| `frontend/tsconfig.json` | TypeScript strict |
| `frontend/index.html` | Trang gốc |
| `frontend/src/main.tsx` | Điểm vào React |
| `frontend/src/types.ts` | Kiểu TypeScript khớp 1-1 `backend/app/schemas.py` |
| `frontend/src/api.ts` | `fetch` thuần + `ApiError` + toàn bộ hàm gọi API |
| `frontend/src/lib/format.ts` | Hàm thuần: định dạng, hình học thanh tiến độ, ngày, thông điệp lỗi |
| `frontend/src/lib/useAsync.ts` | Hook nạp dữ liệu dùng chung (loading / error / reload) |
| `frontend/src/context/CurrentEmployee.tsx` | Nhân viên đang thao tác, lưu `localStorage` |
| `frontend/src/components/Layout.tsx` | Khung trang: header, nav, `<Outlet />` |
| `frontend/src/components/EmployeePicker.tsx` | Dropdown "Đang thao tác với tư cách" |
| `frontend/src/components/ErrorBox.tsx` | Hiển thị lỗi thống nhất |
| `frontend/src/components/StatusBadge.tsx` | Nhãn trạng thái KPI và trạng thái trích xuất |
| `frontend/src/pages/SetupPage.tsx` | Trang Thiết lập |
| `frontend/src/pages/ReportPage.tsx` | Trang Nộp báo cáo |
| `frontend/src/pages/ReviewPage.tsx` | Trang Hàng đợi duyệt |
| `frontend/src/pages/DashboardPage.tsx` | Trang Dashboard |
| `frontend/src/App.tsx` | Định tuyến |
| `frontend/src/index.css` | Toàn bộ CSS |
| `tests/e2e/run_e2e.py` | Dọn cổng + DB tạm, rồi gọi `with_server.py` |
| `tests/e2e/full_flow.py` | Kịch bản Playwright trọn vòng |
| `frontend/README.md` | Hướng dẫn chạy |

### Quy ước `data-testid`

Kịch bản Playwright ở Task 8 bám vào các `data-testid` dưới đây. Các task dựng
trang **phải** đặt đúng tên này, nếu không Task 8 sẽ hỏng.

| Trang | `data-testid` |
|---|---|
| Layout | `nav-setup`, `nav-report`, `nav-review`, `nav-dashboard`, `employee-picker` |
| Lỗi | `error-box` |
| Thiết lập | `employee-form-name`, `employee-form-email`, `employee-form-submit`, `employee-row`, `kpi-form-name`, `kpi-form-target`, `kpi-form-unit`, `kpi-form-owner`, `kpi-form-start`, `kpi-form-end`, `kpi-form-submit`, `kpi-row`, `task-form-title`, `task-form-kpi`, `task-form-assignee`, `task-form-submit`, `task-row` |
| Nộp báo cáo | `report-employee`, `report-week`, `report-text`, `report-submit`, `report-result`, `report-status-badge`, `report-kpi-suggestion`, `report-task-suggestion`, `report-blocker`, `report-reextract` |
| Hàng đợi duyệt | `kpi-suggestion-row`, `kpi-row-select`, `kpi-row-delta`, `kpi-row-note`, `kpi-row-approve`, `kpi-row-reject`, `task-suggestion-row`, `task-row-select`, `task-row-approve`, `task-row-reject`, `queue-empty` |
| Dashboard | `kpi-card`, `kpi-card-name`, `kpi-card-actual`, `kpi-card-percent`, `kpi-card-status`, `dashboard-blocker`, `dashboard-no-blocker` |

---

### Task 1: Scaffold dự án và tầng hàm thuần

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/lib/format.ts`
- Test: `frontend/src/lib/format.test.ts`

**Interfaces:**
- Consumes: (không có — task đầu tiên)
- Produces:
  - `detailToMessage(detail: unknown): string`
  - `clamp(value: number, min: number, max: number): number`
  - `barGeometry(actual: number, target: number, expected: number): { fillPercent: number; markerPercent: number }`
  - `formatPercent(fraction: number): string` — nhận **phân số**, trả chuỗi có dấu `%`
  - `formatNumber(value: number): string`
  - `mondayOf(value: Date): Date`
  - `toIsoDate(value: Date): string` — `yyyy-mm-dd` theo giờ **địa phương**

- [ ] **Step 1: Tạo `frontend/package.json`**

```json
{
  "name": "kpi-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.2",
    "typescript": "^5.6.3",
    "vite": "^5.4.9",
    "vitest": "^2.1.3"
  }
}
```

- [ ] **Step 2: Tạo `frontend/vite.config.ts`**

`strictPort: true` là bắt buộc — xem Global Constraints.

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 5173,
    // Thà chết hẳn còn hơn nhảy sang 5174: cổng khác sẽ trượt CORS của backend
    // và biểu hiện thành một lỗi rất khó lần ra nguyên nhân.
    strictPort: true,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
```

- [ ] **Step 3: Tạo `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vite/client"]
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Tạo `frontend/index.html`**

```html
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Báo cáo tuần &amp; KPI</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Cài dependency**

Chạy từ `frontend/`: `npm install`
Kỳ vọng: tạo `node_modules/` và `package-lock.json`, không có lỗi.

Lưu ý: `.gitignore` ở gốc repo đã có `node_modules/` và `dist/`, nên **không**
cần tạo `frontend/.gitignore`.

- [ ] **Step 6: Viết test thất bại cho `lib/format.ts`**

Tạo `frontend/src/lib/format.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import {
  barGeometry,
  clamp,
  detailToMessage,
  formatNumber,
  formatPercent,
  mondayOf,
  toIsoDate,
} from './format'

describe('detailToMessage', () => {
  it('trả nguyên chuỗi khi backend gửi detail dạng chuỗi', () => {
    expect(detailToMessage('Không tìm thấy báo cáo 7')).toBe('Không tìm thấy báo cáo 7')
  })

  it('ghép mảng lỗi Pydantic thành một câu, bỏ tiền tố "body"', () => {
    const detail = [
      { loc: ['body', 'target_value'], msg: 'Input should be greater than 0', type: 'greater_than' },
      { loc: ['body', 'unit'], msg: 'Field required', type: 'missing' },
    ]
    expect(detailToMessage(detail)).toBe(
      'target_value: Input should be greater than 0; unit: Field required',
    )
  })

  it('có câu dự phòng khi detail là undefined', () => {
    expect(detailToMessage(undefined)).toBe('Đã xảy ra lỗi không xác định.')
  })

  it('có câu dự phòng khi detail là một object lạ', () => {
    expect(detailToMessage({ weird: true })).toBe('Đã xảy ra lỗi không xác định.')
  })

  it('coi chuỗi rỗng như không có thông tin', () => {
    expect(detailToMessage('   ')).toBe('Đã xảy ra lỗi không xác định.')
  })
})

describe('clamp', () => {
  it('kẹp hai đầu', () => {
    expect(clamp(-5, 0, 100)).toBe(0)
    expect(clamp(150, 0, 100)).toBe(100)
    expect(clamp(42, 0, 100)).toBe(42)
  })

  it('trả min khi giá trị không hữu hạn', () => {
    expect(clamp(Number.NaN, 0, 100)).toBe(0)
    expect(clamp(Number.POSITIVE_INFINITY, 0, 100)).toBe(0)
  })
})

describe('barGeometry', () => {
  it('tính phần trăm lấp đầy và vị trí mốc kỳ vọng', () => {
    expect(barGeometry(40, 100, 85)).toEqual({ fillPercent: 40, markerPercent: 85 })
  })

  it('kẹp phần lấp đầy về 100 khi vượt chỉ tiêu', () => {
    expect(barGeometry(150, 100, 100)).toEqual({ fillPercent: 100, markerPercent: 100 })
  })

  it('trả 0 khi target không dương, thay vì chia cho 0', () => {
    expect(barGeometry(10, 0, 5)).toEqual({ fillPercent: 0, markerPercent: 0 })
  })
})

describe('formatPercent', () => {
  it('nhận phân số và trả về số phần trăm', () => {
    // backend trả percent_complete = actual / target, tức 0.4 nghĩa là 40%
    expect(formatPercent(0.4)).toBe('40%')
  })

  it('làm tròn tới một chữ số thập phân', () => {
    expect(formatPercent(0.8571)).toBe('85.7%')
  })

  it('không kẹp trên 100%', () => {
    expect(formatPercent(1.2)).toBe('120%')
  })
})

describe('formatNumber', () => {
  it('bỏ phần thập phân thừa', () => {
    expect(formatNumber(100)).toBe('100')
    expect(formatNumber(40.5)).toBe('40.5')
  })
})

describe('mondayOf', () => {
  it('giữ nguyên khi đã là thứ Hai', () => {
    // 2026-09-07 là thứ Hai
    expect(toIsoDate(mondayOf(new Date(2026, 8, 7)))).toBe('2026-09-07')
  })

  it('lùi về thứ Hai đầu tuần khi ở giữa tuần', () => {
    // 2026-09-11 là thứ Sáu
    expect(toIsoDate(mondayOf(new Date(2026, 8, 11)))).toBe('2026-09-07')
  })

  it('coi Chủ nhật là cuối tuần đó, không phải đầu tuần sau', () => {
    // 2026-09-13 là Chủ nhật
    expect(toIsoDate(mondayOf(new Date(2026, 8, 13)))).toBe('2026-09-07')
  })
})

describe('toIsoDate', () => {
  it('dùng giờ địa phương, không lệch ngày như toISOString', () => {
    // Ở múi giờ UTC+7, new Date(2026, 8, 11).toISOString() cho "2026-09-10T17:00:00Z"
    // — lùi mất một ngày. toIsoDate phải miễn nhiễm với chuyện đó.
    expect(toIsoDate(new Date(2026, 8, 11))).toBe('2026-09-11')
  })
})
```

- [ ] **Step 7: Chạy test để xác nhận nó thất bại**

Chạy từ `frontend/`: `npm test`
Kỳ vọng: FAIL — `Failed to resolve import "./format"`.

- [ ] **Step 8: Viết `frontend/src/lib/format.ts`**

```ts
/** Hàm thuần dùng chung. Không chạm DOM, không chạm mạng. */

const UNKNOWN_ERROR = 'Đã xảy ra lỗi không xác định.'

interface PydanticError {
  loc?: unknown
  msg?: unknown
}

/**
 * Backend trả `detail` ở hai dạng: chuỗi (từ các exception handler nghiệp vụ)
 * và mảng lỗi Pydantic (từ RequestValidationError). Hàm này đưa cả hai — cùng
 * mọi dạng lạ khác — về đúng một câu hiển thị được.
 */
export function detailToMessage(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail.trim() === '' ? UNKNOWN_ERROR : detail
  }

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item.trim()
        if (item === null || typeof item !== 'object') return ''
        const entry = item as PydanticError
        const message = typeof entry.msg === 'string' ? entry.msg : ''
        const field = Array.isArray(entry.loc)
          ? entry.loc.filter((part) => part !== 'body').join('.')
          : ''
        if (message === '') return ''
        return field === '' ? message : `${field}: ${message}`
      })
      .filter((part) => part !== '')
    if (parts.length > 0) return parts.join('; ')
  }

  return UNKNOWN_ERROR
}

export function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min
  return Math.min(max, Math.max(min, value))
}

/**
 * Hình học thanh tiến độ. Khác với phần trăm hiển thị, hai số này **phải** kẹp
 * trong 0–100, nếu không thanh sẽ tràn ra khỏi khung.
 */
export function barGeometry(
  actual: number,
  target: number,
  expected: number,
): { fillPercent: number; markerPercent: number } {
  if (!(target > 0)) return { fillPercent: 0, markerPercent: 0 }
  return {
    fillPercent: clamp((actual / target) * 100, 0, 100),
    markerPercent: clamp((expected / target) * 100, 0, 100),
  }
}

/** Nhận **phân số** (backend trả `actual / target`), trả chuỗi phần trăm. */
export function formatPercent(fraction: number): string {
  if (!Number.isFinite(fraction)) return '0%'
  return `${formatNumber(Math.round(fraction * 1000) / 10)}%`
}

export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return '0'
  return String(Math.round(value * 100) / 100)
}

/** Đưa một ngày về thứ Hai cùng tuần. Chủ nhật thuộc về tuần vừa qua. */
export function mondayOf(value: Date): Date {
  const result = new Date(value.getFullYear(), value.getMonth(), value.getDate())
  const weekday = result.getDay() // 0 = Chủ nhật
  result.setDate(result.getDate() + (weekday === 0 ? -6 : 1 - weekday))
  return result
}

/**
 * `yyyy-mm-dd` theo giờ **địa phương**. Không dùng `toISOString()`: ở múi giờ
 * dương nó quy đổi nửa đêm địa phương về ngày hôm trước theo UTC, và ô `week_start`
 * sẽ lệch một ngày.
 */
export function toIsoDate(value: Date): string {
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${value.getFullYear()}-${month}-${day}`
}
```

- [ ] **Step 9: Chạy test để xác nhận nó pass**

Chạy từ `frontend/`: `npm test`
Kỳ vọng: PASS, toàn bộ test trong `format.test.ts`.

- [ ] **Step 10: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src/lib/format.ts frontend/src/lib/format.test.ts
git commit -m "feat(frontend): scaffold Vite + Vitest va tang ham thuan"
```

---

### Task 2: Kiểu dữ liệu và tầng API

**Files:**
- Create: `frontend/src/types.ts`, `frontend/src/api.ts`
- Test: `frontend/src/lib/api.test.ts`

**Interfaces:**
- Consumes: `detailToMessage` từ `lib/format.ts` (Task 1)
- Produces:
  - `ApiError` (class, có `status: number` và `detail: unknown`)
  - Kiểu: `Employee`, `Kpi`, `Task`, `Report`, `KpiSuggestion`, `TaskSuggestion`, `Blocker`, `SuggestionContext`, `SuggestionQueue`, `DashboardItem`, `ExtractionStatus`, `SuggestionStatus`, `TaskStatus`
  - Hàm: `listEmployees`, `createEmployee`, `listKpis`, `createKpi`, `updateKpi`, `listTasks`, `createTask`, `updateTask`, `listReports`, `getReport`, `createReport`, `reextractReport`, `listSuggestions`, `approveKpiSuggestion`, `rejectKpiSuggestion`, `approveTaskSuggestion`, `rejectTaskSuggestion`, `getDashboard`

- [ ] **Step 1: Tạo `frontend/src/types.ts`**

Khớp 1-1 với `backend/app/schemas.py`.

```ts
export type ExtractionStatus = 'pending' | 'extracted' | 'failed'
export type SuggestionStatus = 'pending' | 'approved' | 'rejected'
export type TaskStatus = 'todo' | 'doing' | 'done'
export type KpiStatus = 'on_track' | 'at_risk' | 'completed'

export interface Employee {
  id: number
  name: string
  email: string
}

export interface Kpi {
  id: number
  name: string
  target_value: number
  unit: string
  owner_id: number
  period_start: string
  period_end: string
}

export interface Task {
  id: number
  title: string
  kpi_id: number
  assignee_id: number
  status: TaskStatus
  completed_at: string | null
}

export interface KpiSuggestion {
  id: number
  report_id: number
  suggested_kpi_id: number | null
  suggested_delta: number
  evidence: string
  status: SuggestionStatus
  final_kpi_id: number | null
  final_delta: number | null
  review_note: string | null
}

export interface TaskSuggestion {
  id: number
  report_id: number
  suggested_task_id: number | null
  raw_text: string
  status: SuggestionStatus
  final_task_id: number | null
}

export interface Blocker {
  id: number
  report_id: number
  description: string
  related_kpi_id: number | null
}

export interface Report {
  id: number
  employee_id: number
  week_start: string
  raw_text: string
  extraction_status: ExtractionStatus
  extraction_error: string | null
  provider_name: string | null
  kpi_suggestions: KpiSuggestion[]
  task_suggestions: TaskSuggestion[]
  blockers: Blocker[]
}

/** Một dòng trong hàng đợi duyệt, đã kèm ngữ cảnh để trang không phải gọi thêm. */
export interface SuggestionContext {
  id: number
  report_id: number
  employee_name: string
  week_start: string
  suggested_kpi_id: number | null
  suggested_delta: number | null
  suggested_task_id: number | null
  raw_text: string | null
  evidence: string | null
}

export interface SuggestionQueue {
  kpi_updates: SuggestionContext[]
  task_completions: SuggestionContext[]
}

export interface DashboardItem {
  kpi_id: number
  kpi_name: string
  unit: string
  owner_name: string
  period_start: string
  period_end: string
  actual_value: number
  target_value: number
  expected_value: number
  /** Phân số 0–1, không phải số phần trăm. */
  percent_complete: number
  status: KpiStatus
  at_risk: boolean
}

export interface EmployeeCreate {
  name: string
  email: string
}

export interface KpiCreate {
  name: string
  target_value: number
  unit: string
  owner_id: number
  period_start: string
  period_end: string
}

export interface KpiPatch {
  name?: string
  target_value?: number
  unit?: string
  period_start?: string
  period_end?: string
}

export interface TaskCreate {
  title: string
  kpi_id: number
  assignee_id: number
}

export interface TaskPatch {
  title?: string
  status?: TaskStatus
}

export interface ReportCreate {
  employee_id: number
  week_start: string
  raw_text: string
}

export interface KpiApprovePayload {
  final_kpi_id: number
  final_delta: number
  note: string | null
}
```

- [ ] **Step 2: Viết test thất bại cho `api.ts`**

Tạo `frontend/src/lib/api.test.ts`:

```ts
import { describe, it, expect, afterEach, vi } from 'vitest'
import { ApiError, createEmployee, getDashboard, listEmployees } from '../api'

function mockFetch(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const stub = vi.fn().mockResolvedValue(response as Response)
  vi.stubGlobal('fetch', stub)
  return stub
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('request thành công', () => {
  it('trả về JSON đã parse', async () => {
    mockFetch({ ok: true, status: 200, json: async () => [{ id: 1, name: 'An', email: 'a@b.c' }] })
    await expect(listEmployees()).resolves.toEqual([{ id: 1, name: 'An', email: 'a@b.c' }])
  })

  it('gửi Content-Type json kèm body khi POST', async () => {
    const stub = mockFetch({ ok: true, status: 201, json: async () => ({ id: 1 }) })
    await createEmployee({ name: 'An', email: 'a@b.c' })
    const init = stub.mock.calls[0][1] as RequestInit
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    expect(init.body).toBe(JSON.stringify({ name: 'An', email: 'a@b.c' }))
  })
})

describe('lỗi HTTP', () => {
  it('409 ném ApiError mang đúng status và thông điệp từ detail chuỗi', async () => {
    mockFetch({ ok: false, status: 409, json: async () => ({ detail: 'Email a@b.c đã được dùng' }) })
    const error = await createEmployee({ name: 'An', email: 'a@b.c' }).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
    expect(error.message).toBe('Email a@b.c đã được dùng')
  })

  it('404 ném ApiError với status 404', async () => {
    mockFetch({ ok: false, status: 404, json: async () => ({ detail: 'Không tìm thấy KPI 9' }) })
    const error = await getDashboard().catch((e) => e)
    expect(error.status).toBe(404)
  })

  it('422 ghép mảng lỗi Pydantic thành một câu', async () => {
    mockFetch({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [{ loc: ['body', 'target_value'], msg: 'Input should be greater than 0' }],
      }),
    })
    const error = await getDashboard().catch((e) => e)
    expect(error.status).toBe(422)
    expect(error.message).toBe('target_value: Input should be greater than 0')
  })

  it('không sập khi thân phản hồi lỗi không phải JSON', async () => {
    mockFetch({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => {
        throw new Error('not json')
      },
    })
    const error = await getDashboard().catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(500)
  })
})

describe('lỗi mạng', () => {
  it('cho status 0 để UI phân biệt được "backend chưa bật"', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const error = await getDashboard().catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(0)
    expect(error.message).toContain('backend')
  })
})
```

- [ ] **Step 3: Chạy test để xác nhận nó thất bại**

Chạy từ `frontend/`: `npm test`
Kỳ vọng: FAIL — `Failed to resolve import "../api"`.

- [ ] **Step 4: Viết `frontend/src/api.ts`**

```ts
import { detailToMessage } from './lib/format'
import type {
  DashboardItem,
  Employee,
  EmployeeCreate,
  Kpi,
  KpiApprovePayload,
  KpiCreate,
  KpiPatch,
  KpiSuggestion,
  Report,
  ReportCreate,
  SuggestionQueue,
  Task,
  TaskCreate,
  TaskPatch,
  TaskSuggestion,
} from './types'

export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000'

const NETWORK_MESSAGE =
  'Không kết nối được tới backend. Hãy chắc chắn uvicorn đang chạy ở cổng 8000.'

/** Mọi lỗi đi qua tầng API đều mang hình dạng này. `status = 0` nghĩa là lỗi mạng. */
export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, detail: unknown) {
    super(detailToMessage(detail))
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const init: RequestInit = { method }
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(body)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, init)
  } catch {
    // fetch chỉ reject khi không tới được server; mọi mã lỗi HTTP đều resolve.
    throw new ApiError(0, NETWORK_MESSAGE)
  }

  if (!response.ok) {
    let detail: unknown
    try {
      detail = ((await response.json()) as { detail?: unknown }).detail
    } catch {
      detail = response.statusText
    }
    throw new ApiError(response.status, detail)
  }

  return (await response.json()) as T
}

export const listEmployees = () => request<Employee[]>('/api/employees')
export const createEmployee = (payload: EmployeeCreate) =>
  request<Employee>('/api/employees', 'POST', payload)

export const listKpis = () => request<Kpi[]>('/api/kpis')
export const createKpi = (payload: KpiCreate) => request<Kpi>('/api/kpis', 'POST', payload)
export const updateKpi = (id: number, payload: KpiPatch) =>
  request<Kpi>(`/api/kpis/${id}`, 'PATCH', payload)

export const listTasks = () => request<Task[]>('/api/tasks')
export const createTask = (payload: TaskCreate) => request<Task>('/api/tasks', 'POST', payload)
export const updateTask = (id: number, payload: TaskPatch) =>
  request<Task>(`/api/tasks/${id}`, 'PATCH', payload)

export const listReports = () => request<Report[]>('/api/reports')
export const getReport = (id: number) => request<Report>(`/api/reports/${id}`)
export const createReport = (payload: ReportCreate) =>
  request<Report>('/api/reports', 'POST', payload)
export const reextractReport = (id: number) =>
  request<Report>(`/api/reports/${id}/extract`, 'POST', {})

export const listSuggestions = (status = 'pending') =>
  request<SuggestionQueue>(`/api/suggestions?status=${status}`)
export const approveKpiSuggestion = (id: number, payload: KpiApprovePayload) =>
  request<KpiSuggestion>(`/api/suggestions/kpi/${id}/approve`, 'POST', payload)
export const rejectKpiSuggestion = (id: number) =>
  request<KpiSuggestion>(`/api/suggestions/kpi/${id}/reject`, 'POST', {})
export const approveTaskSuggestion = (id: number, finalTaskId: number) =>
  request<TaskSuggestion>(`/api/suggestions/task/${id}/approve`, 'POST', {
    final_task_id: finalTaskId,
  })
export const rejectTaskSuggestion = (id: number) =>
  request<TaskSuggestion>(`/api/suggestions/task/${id}/reject`, 'POST', {})

export const getDashboard = () => request<DashboardItem[]>('/api/dashboard')
```

- [ ] **Step 5: Chạy test để xác nhận nó pass**

Chạy từ `frontend/`: `npm test`
Kỳ vọng: PASS toàn bộ `format.test.ts` và `api.test.ts`.

- [ ] **Step 6: Kiểm tra TypeScript**

Chạy từ `frontend/`: `npx tsc --noEmit`
Kỳ vọng: không lỗi.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts frontend/src/lib/api.test.ts
git commit -m "feat(frontend): kieu du lieu va tang API voi ApiError"
```

---

### Task 3: Khung ứng dụng — hook, context, layout, định tuyến

**Files:**
- Create: `frontend/src/lib/useAsync.ts`, `frontend/src/context/CurrentEmployee.tsx`, `frontend/src/components/ErrorBox.tsx`, `frontend/src/components/StatusBadge.tsx`, `frontend/src/components/EmployeePicker.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/index.css`
- Create (tạm, sẽ thay ở Task 4–7): `frontend/src/pages/SetupPage.tsx`, `frontend/src/pages/ReportPage.tsx`, `frontend/src/pages/ReviewPage.tsx`, `frontend/src/pages/DashboardPage.tsx`

**Interfaces:**
- Consumes: `listEmployees` từ `api.ts` (Task 2)
- Produces:
  - `useAsync<T>(loader: () => Promise<T>, deps: unknown[]): { data: T | undefined; error: Error | undefined; loading: boolean; reload: () => void }`
  - `CurrentEmployeeProvider` (component) và `useCurrentEmployee(): { currentEmployeeId: number | null; setCurrentEmployeeId: (id: number | null) => void }`
  - `<ErrorBox error={unknown} />`
  - `<KpiStatusBadge status={KpiStatus} />` và `<ExtractionStatusBadge status={ExtractionStatus} />`
  - Bốn component trang rỗng, mỗi cái export mặc định

- [ ] **Step 1: Viết `frontend/src/lib/useAsync.ts`**

```ts
import { useCallback, useEffect, useState } from 'react'

export interface AsyncState<T> {
  data: T | undefined
  error: Error | undefined
  loading: boolean
  reload: () => void
}

/**
 * Nạp dữ liệu cho một trang. Cố tình **không** cache: mỗi lần `reload()` là một
 * lần gọi mạng mới, nên không bao giờ có dữ liệu cũ sau khi người dùng ghi.
 */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | undefined>(undefined)
  const [error, setError] = useState<Error | undefined>(undefined)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  const reload = useCallback(() => setTick((value) => value + 1), [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    loader()
      .then((value) => {
        if (cancelled) return
        setData(value)
        setError(undefined)
      })
      .catch((caught: unknown) => {
        if (cancelled) return
        setError(caught instanceof Error ? caught : new Error(String(caught)))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  return { data, error, loading, reload }
}
```

- [ ] **Step 2: Viết `frontend/src/context/CurrentEmployee.tsx`**

```tsx
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

const STORAGE_KEY = 'kpi.currentEmployeeId'

interface CurrentEmployeeValue {
  currentEmployeeId: number | null
  setCurrentEmployeeId: (id: number | null) => void
}

const CurrentEmployeeContext = createContext<CurrentEmployeeValue>({
  currentEmployeeId: null,
  setCurrentEmployeeId: () => undefined,
})

function readStored(): number | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw === null) return null
    const parsed = Number(raw)
    return Number.isInteger(parsed) ? parsed : null
  } catch {
    // localStorage có thể bị chặn (cửa sổ ẩn danh, thiết lập trình duyệt).
    return null
  }
}

export function CurrentEmployeeProvider({ children }: { children: ReactNode }) {
  const [currentEmployeeId, setState] = useState<number | null>(readStored)

  useEffect(() => {
    try {
      if (currentEmployeeId === null) window.localStorage.removeItem(STORAGE_KEY)
      else window.localStorage.setItem(STORAGE_KEY, String(currentEmployeeId))
    } catch {
      // Không nhớ được thì thôi, không phải lỗi chặn người dùng.
    }
  }, [currentEmployeeId])

  const setCurrentEmployeeId = useCallback((id: number | null) => setState(id), [])

  return (
    <CurrentEmployeeContext.Provider value={{ currentEmployeeId, setCurrentEmployeeId }}>
      {children}
    </CurrentEmployeeContext.Provider>
  )
}

export function useCurrentEmployee(): CurrentEmployeeValue {
  return useContext(CurrentEmployeeContext)
}
```

- [ ] **Step 3: Viết `frontend/src/components/ErrorBox.tsx`**

```tsx
import { ApiError } from '../api'

export function ErrorBox({ error }: { error: unknown }) {
  if (error === null || error === undefined) return null

  const message = error instanceof Error ? error.message : String(error)
  const hint =
    error instanceof ApiError && error.status === 0
      ? 'Chạy `uvicorn app.main:app --reload` trong thư mục backend rồi thử lại.'
      : null

  return (
    <div className="error-box" data-testid="error-box" role="alert">
      <strong>Lỗi:</strong> {message}
      {hint !== null && <div className="error-hint">{hint}</div>}
    </div>
  )
}
```

- [ ] **Step 4: Viết `frontend/src/components/StatusBadge.tsx`**

```tsx
import type { ExtractionStatus, KpiStatus } from '../types'

const KPI_LABEL: Record<KpiStatus, string> = {
  on_track: 'Đúng tiến độ',
  at_risk: 'Có nguy cơ',
  completed: 'Hoàn thành',
}

const EXTRACTION_LABEL: Record<ExtractionStatus, string> = {
  pending: 'Đang chờ',
  extracted: 'Đã trích xuất',
  failed: 'Trích xuất thất bại',
}

export function KpiStatusBadge({ status }: { status: KpiStatus }) {
  return (
    <span className={`badge badge-${status}`} data-testid="kpi-card-status">
      {KPI_LABEL[status]}
    </span>
  )
}

export function ExtractionStatusBadge({ status }: { status: ExtractionStatus }) {
  return (
    <span className={`badge badge-${status}`} data-testid="report-status-badge">
      {EXTRACTION_LABEL[status]}
    </span>
  )
}
```

- [ ] **Step 5: Viết `frontend/src/components/EmployeePicker.tsx`**

```tsx
import { listEmployees } from '../api'
import { useCurrentEmployee } from '../context/CurrentEmployee'
import { useAsync } from '../lib/useAsync'

export function EmployeePicker() {
  const { currentEmployeeId, setCurrentEmployeeId } = useCurrentEmployee()
  const { data: employees } = useAsync(listEmployees, [])

  return (
    <label className="employee-picker">
      Đang thao tác với tư cách:{' '}
      <select
        data-testid="employee-picker"
        value={currentEmployeeId ?? ''}
        onChange={(event) =>
          setCurrentEmployeeId(event.target.value === '' ? null : Number(event.target.value))
        }
      >
        <option value="">— chưa chọn —</option>
        {(employees ?? []).map((employee) => (
          <option key={employee.id} value={employee.id}>
            {employee.name}
          </option>
        ))}
      </select>
    </label>
  )
}
```

- [ ] **Step 6: Viết `frontend/src/components/Layout.tsx`**

```tsx
import { NavLink, Outlet } from 'react-router-dom'
import { EmployeePicker } from './EmployeePicker'

const LINKS = [
  { to: '/dashboard', label: 'Dashboard', testId: 'nav-dashboard' },
  { to: '/report', label: 'Nộp báo cáo', testId: 'nav-report' },
  { to: '/review', label: 'Hàng đợi duyệt', testId: 'nav-review' },
  { to: '/setup', label: 'Thiết lập', testId: 'nav-setup' },
]

export function Layout() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">Báo cáo tuần &amp; KPI</div>
        <nav className="app-nav">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} data-testid={link.testId}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <EmployeePicker />
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 7: Tạo bốn trang rỗng**

Mỗi file dưới đây là bản tạm, sẽ được thay hoàn toàn ở Task 4–7. Mục đích là để
định tuyến chạy được ngay từ task này.

`frontend/src/pages/SetupPage.tsx`:
```tsx
export default function SetupPage() {
  return <h1>Thiết lập</h1>
}
```

`frontend/src/pages/ReportPage.tsx`:
```tsx
export default function ReportPage() {
  return <h1>Nộp báo cáo</h1>
}
```

`frontend/src/pages/ReviewPage.tsx`:
```tsx
export default function ReviewPage() {
  return <h1>Hàng đợi duyệt</h1>
}
```

`frontend/src/pages/DashboardPage.tsx`:
```tsx
export default function DashboardPage() {
  return <h1>Dashboard</h1>
}
```

- [ ] **Step 8: Viết `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { CurrentEmployeeProvider } from './context/CurrentEmployee'
import DashboardPage from './pages/DashboardPage'
import ReportPage from './pages/ReportPage'
import ReviewPage from './pages/ReviewPage'
import SetupPage from './pages/SetupPage'

export default function App() {
  return (
    <CurrentEmployeeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/setup" element={<SetupPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CurrentEmployeeProvider>
  )
}
```

- [ ] **Step 9: Viết `frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 10: Viết `frontend/src/index.css`**

```css
:root {
  --bg: #f6f7f9;
  --surface: #ffffff;
  --border: #d8dce3;
  --text: #1c2230;
  --muted: #667085;
  --accent: #2563eb;
  --ok: #15803d;
  --warn: #b45309;
  --danger: #b91c1c;
  --radius: 8px;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.5 "Segoe UI", system-ui, sans-serif;
}

.app-header {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  padding: 12px 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.app-title { font-weight: 700; }
.app-nav { display: flex; gap: 4px; }

.app-nav a {
  padding: 6px 12px;
  border-radius: var(--radius);
  color: var(--muted);
  text-decoration: none;
}

.app-nav a.active { background: var(--accent); color: #fff; }
.employee-picker { margin-left: auto; color: var(--muted); }
.app-main { padding: 24px; max-width: 1100px; }

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  margin-bottom: 20px;
}

h1 { font-size: 22px; margin: 0 0 20px; }
h2 { font-size: 17px; margin: 0 0 12px; }

label { display: block; margin-bottom: 8px; font-size: 13px; color: var(--muted); }

input, select, textarea {
  width: 100%;
  padding: 7px 9px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font: inherit;
  background: #fff;
  color: inherit;
}

textarea { min-height: 140px; resize: vertical; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.row { display: flex; gap: 8px; align-items: flex-end; flex-wrap: wrap; }

button {
  padding: 7px 14px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
  font: inherit;
  cursor: pointer;
}

button.secondary { background: #fff; color: var(--text); border-color: var(--border); }
button:disabled { opacity: 0.5; cursor: not-allowed; }

table { width: 100%; border-collapse: collapse; }
th, td { padding: 8px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
th { font-size: 12px; text-transform: uppercase; color: var(--muted); }

.badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge-on_track, .badge-extracted { background: #dcfce7; color: var(--ok); }
.badge-at_risk, .badge-pending { background: #fef3c7; color: var(--warn); }
.badge-completed { background: #dbeafe; color: var(--accent); }
.badge-failed { background: #fee2e2; color: var(--danger); }

.error-box {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  color: var(--danger);
  border-radius: var(--radius);
  padding: 10px 14px;
  margin-bottom: 16px;
}

.error-hint { color: var(--muted); font-size: 13px; margin-top: 4px; }
.muted { color: var(--muted); }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 16px; }
.kpi-card-top { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.kpi-percent { font-size: 26px; font-weight: 700; }

.bar { position: relative; height: 12px; background: #e7eaf0; border-radius: 999px; margin: 10px 0 6px; }
.bar-fill { height: 100%; background: var(--accent); border-radius: 999px; }
.bar-fill.at_risk { background: var(--warn); }
.bar-fill.completed { background: var(--ok); }
.bar-marker { position: absolute; top: -3px; width: 2px; height: 18px; background: var(--text); }
```

- [ ] **Step 11: Kiểm tra build và mở thử**

Chạy từ `frontend/`: `npx tsc --noEmit && npm run build`
Kỳ vọng: không lỗi TypeScript, build thành công.

Chạy từ `frontend/`: `npm run dev`
Kỳ vọng: log in ra đúng `http://localhost:5173/`. Mở thử, thấy header với 4 link
và dropdown; bấm qua lại 4 trang thấy 4 tiêu đề. Dừng server bằng Ctrl+C.

- [ ] **Step 12: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): khung ung dung, dinh tuyen va hook useAsync"
```

---

### Task 4: Trang Thiết lập

**Files:**
- Modify: `frontend/src/pages/SetupPage.tsx` (thay hoàn toàn bản tạm từ Task 3)

**Interfaces:**
- Consumes: `useAsync` (Task 3), `ErrorBox` (Task 3), `useCurrentEmployee` (Task 3), `listEmployees`/`createEmployee`/`listKpis`/`createKpi`/`updateKpi`/`listTasks`/`createTask`/`updateTask` (Task 2), `toIsoDate`/`formatNumber` (Task 1)
- Produces: `data-testid` của trang Thiết lập (bảng ở mục "Quy ước `data-testid`")

- [ ] **Step 1: Viết `frontend/src/pages/SetupPage.tsx`**

```tsx
import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  createEmployee,
  createKpi,
  createTask,
  listEmployees,
  listKpis,
  listTasks,
  updateKpi,
  updateTask,
} from '../api'
import { ErrorBox } from '../components/ErrorBox'
import { formatNumber, toIsoDate } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import type { TaskStatus } from '../types'

const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  todo: 'Chưa làm',
  doing: 'Đang làm',
  done: 'Xong',
}

export default function SetupPage() {
  const employees = useAsync(listEmployees, [])
  const kpis = useAsync(listKpis, [])
  const tasks = useAsync(listTasks, [])

  const employeeList = employees.data ?? []
  const kpiList = kpis.data ?? []
  const taskList = tasks.data ?? []

  const [employeeName, setEmployeeName] = useState('')
  const [employeeEmail, setEmployeeEmail] = useState('')
  const [employeeError, setEmployeeError] = useState<unknown>(null)

  const today = new Date()
  const [kpiName, setKpiName] = useState('')
  const [kpiTarget, setKpiTarget] = useState('100')
  const [kpiUnit, setKpiUnit] = useState('')
  const [kpiOwner, setKpiOwner] = useState('')
  const [kpiStart, setKpiStart] = useState(toIsoDate(today))
  const [kpiEnd, setKpiEnd] = useState(toIsoDate(today))
  const [kpiError, setKpiError] = useState<unknown>(null)

  const [taskTitle, setTaskTitle] = useState('')
  const [taskKpi, setTaskKpi] = useState('')
  const [taskAssignee, setTaskAssignee] = useState('')
  const [taskError, setTaskError] = useState<unknown>(null)

  async function submitEmployee(event: FormEvent) {
    event.preventDefault()
    setEmployeeError(null)
    try {
      await createEmployee({ name: employeeName, email: employeeEmail })
      setEmployeeName('')
      setEmployeeEmail('')
      employees.reload()
    } catch (caught) {
      setEmployeeError(caught)
    }
  }

  async function submitKpi(event: FormEvent) {
    event.preventDefault()
    setKpiError(null)
    try {
      await createKpi({
        name: kpiName,
        target_value: Number(kpiTarget),
        unit: kpiUnit,
        owner_id: Number(kpiOwner),
        period_start: kpiStart,
        period_end: kpiEnd,
      })
      setKpiName('')
      setKpiUnit('')
      kpis.reload()
    } catch (caught) {
      setKpiError(caught)
    }
  }

  async function submitTask(event: FormEvent) {
    event.preventDefault()
    setTaskError(null)
    try {
      await createTask({
        title: taskTitle,
        kpi_id: Number(taskKpi),
        assignee_id: Number(taskAssignee),
      })
      setTaskTitle('')
      tasks.reload()
    } catch (caught) {
      setTaskError(caught)
    }
  }

  async function renameKpi(id: number, current: string) {
    const next = window.prompt('Tên KPI mới', current)
    if (next === null || next.trim() === '') return
    try {
      await updateKpi(id, { name: next.trim() })
      kpis.reload()
    } catch (caught) {
      setKpiError(caught)
    }
  }

  async function retargetKpi(id: number, current: number) {
    const next = window.prompt('Chỉ tiêu mới', String(current))
    if (next === null || Number.isNaN(Number(next))) return
    try {
      await updateKpi(id, { target_value: Number(next) })
      kpis.reload()
    } catch (caught) {
      setKpiError(caught)
    }
  }

  async function changeTaskStatus(id: number, status: TaskStatus) {
    try {
      await updateTask(id, { status })
      tasks.reload()
    } catch (caught) {
      setTaskError(caught)
    }
  }

  const employeeName4 = (id: number) =>
    employeeList.find((item) => item.id === id)?.name ?? `#${id}`
  const kpiName4 = (id: number) => kpiList.find((item) => item.id === id)?.name ?? `#${id}`

  return (
    <div>
      <h1>Thiết lập</h1>
      <ErrorBox error={employees.error ?? kpis.error ?? tasks.error} />

      <section className="card">
        <h2>Nhân viên</h2>
        <ErrorBox error={employeeError} />
        <form onSubmit={submitEmployee}>
          <div className="form-grid">
            <label>
              Họ tên
              <input
                data-testid="employee-form-name"
                required
                value={employeeName}
                onChange={(event) => setEmployeeName(event.target.value)}
              />
            </label>
            <label>
              Email
              <input
                data-testid="employee-form-email"
                required
                value={employeeEmail}
                onChange={(event) => setEmployeeEmail(event.target.value)}
              />
            </label>
          </div>
          <button data-testid="employee-form-submit" type="submit">
            Thêm nhân viên
          </button>
        </form>

        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Họ tên</th>
              <th>Email</th>
            </tr>
          </thead>
          <tbody>
            {employeeList.map((employee) => (
              <tr key={employee.id} data-testid="employee-row">
                <td>{employee.id}</td>
                <td>{employee.name}</td>
                <td>{employee.email}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {employeeList.length === 0 && <p className="muted">Chưa có nhân viên nào.</p>}
      </section>

      <section className="card">
        <h2>KPI</h2>
        <ErrorBox error={kpiError} />
        <form onSubmit={submitKpi}>
          <div className="form-grid">
            <label>
              Tên KPI
              <input
                data-testid="kpi-form-name"
                required
                value={kpiName}
                onChange={(event) => setKpiName(event.target.value)}
              />
            </label>
            <label>
              Chỉ tiêu
              <input
                data-testid="kpi-form-target"
                type="number"
                step="any"
                required
                value={kpiTarget}
                onChange={(event) => setKpiTarget(event.target.value)}
              />
            </label>
            <label>
              Đơn vị
              <input
                data-testid="kpi-form-unit"
                required
                value={kpiUnit}
                onChange={(event) => setKpiUnit(event.target.value)}
              />
            </label>
            <label>
              Người phụ trách
              <select
                data-testid="kpi-form-owner"
                required
                value={kpiOwner}
                onChange={(event) => setKpiOwner(event.target.value)}
              >
                <option value="">— chọn —</option>
                {employeeList.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Bắt đầu kỳ
              <input
                data-testid="kpi-form-start"
                type="date"
                required
                value={kpiStart}
                onChange={(event) => setKpiStart(event.target.value)}
              />
            </label>
            <label>
              Kết thúc kỳ
              <input
                data-testid="kpi-form-end"
                type="date"
                required
                value={kpiEnd}
                onChange={(event) => setKpiEnd(event.target.value)}
              />
            </label>
          </div>
          <button data-testid="kpi-form-submit" type="submit">
            Thêm KPI
          </button>
        </form>

        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Chỉ tiêu</th>
              <th>Phụ trách</th>
              <th>Kỳ</th>
              <th>Sửa</th>
            </tr>
          </thead>
          <tbody>
            {kpiList.map((kpi) => (
              <tr key={kpi.id} data-testid="kpi-row">
                <td>{kpi.id}</td>
                <td>{kpi.name}</td>
                <td>
                  {formatNumber(kpi.target_value)} {kpi.unit}
                </td>
                <td>{employeeName4(kpi.owner_id)}</td>
                <td>
                  {kpi.period_start} → {kpi.period_end}
                </td>
                <td className="row">
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => renameKpi(kpi.id, kpi.name)}
                  >
                    Đổi tên
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => retargetKpi(kpi.id, kpi.target_value)}
                  >
                    Đổi chỉ tiêu
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {kpiList.length === 0 && <p className="muted">Chưa có KPI nào.</p>}
      </section>

      <section className="card">
        <h2>Công việc</h2>
        <ErrorBox error={taskError} />
        <form onSubmit={submitTask}>
          <div className="form-grid">
            <label>
              Tiêu đề
              <input
                data-testid="task-form-title"
                required
                value={taskTitle}
                onChange={(event) => setTaskTitle(event.target.value)}
              />
            </label>
            <label>
              Thuộc KPI
              <select
                data-testid="task-form-kpi"
                required
                value={taskKpi}
                onChange={(event) => setTaskKpi(event.target.value)}
              >
                <option value="">— chọn —</option>
                {kpiList.map((kpi) => (
                  <option key={kpi.id} value={kpi.id}>
                    {kpi.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Người thực hiện
              <select
                data-testid="task-form-assignee"
                required
                value={taskAssignee}
                onChange={(event) => setTaskAssignee(event.target.value)}
              >
                <option value="">— chọn —</option>
                {employeeList.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <button data-testid="task-form-submit" type="submit">
            Thêm công việc
          </button>
        </form>

        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Tiêu đề</th>
              <th>KPI</th>
              <th>Người thực hiện</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {taskList.map((task) => (
              <tr key={task.id} data-testid="task-row">
                <td>{task.id}</td>
                <td>{task.title}</td>
                <td>{kpiName4(task.kpi_id)}</td>
                <td>{employeeName4(task.assignee_id)}</td>
                <td>
                  <select
                    value={task.status}
                    onChange={(event) =>
                      changeTaskStatus(task.id, event.target.value as TaskStatus)
                    }
                  >
                    {(Object.keys(TASK_STATUS_LABEL) as TaskStatus[]).map((status) => (
                      <option key={status} value={status}>
                        {TASK_STATUS_LABEL[status]}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {taskList.length === 0 && <p className="muted">Chưa có công việc nào.</p>}
      </section>
    </div>
  )
}
```

- [ ] **Step 2: Kiểm tra kiểu và test hồi quy**

Chạy từ `frontend/`: `npx tsc --noEmit && npm test`
Kỳ vọng: không lỗi kiểu; toàn bộ test Vitest vẫn PASS.

- [ ] **Step 3: Kiểm tra thủ công trên trình duyệt**

Mở hai terminal.
Terminal 1, từ `backend/`: `uvicorn app.main:app --reload`
Terminal 2, từ `frontend/`: `npm run dev`

Mở `http://localhost:5173/setup`. Kỳ vọng:
- Thêm một nhân viên → xuất hiện ngay trong bảng.
- Thêm nhân viên thứ hai **trùng email** → hộp lỗi đỏ hiện "Email ... đã được dùng", bảng không đổi.
- Thêm một KPI và một công việc → xuất hiện trong bảng tương ứng.
- Không có lỗi CORS trong console của trình duyệt.

Dừng cả hai server.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SetupPage.tsx
git commit -m "feat(frontend): trang Thiet lap"
```

---

### Task 5: Trang Nộp báo cáo

**Files:**
- Modify: `frontend/src/pages/ReportPage.tsx` (thay hoàn toàn bản tạm từ Task 3)

**Interfaces:**
- Consumes: `useAsync`, `ErrorBox`, `ExtractionStatusBadge`, `useCurrentEmployee` (Task 3); `listEmployees`/`listKpis`/`listTasks`/`listReports`/`createReport`/`reextractReport` (Task 2); `mondayOf`/`toIsoDate`/`formatNumber` (Task 1)
- Produces: `data-testid` của trang Nộp báo cáo

- [ ] **Step 1: Viết `frontend/src/pages/ReportPage.tsx`**

```tsx
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  createReport,
  listEmployees,
  listKpis,
  listReports,
  listTasks,
  reextractReport,
} from '../api'
import { ErrorBox } from '../components/ErrorBox'
import { ExtractionStatusBadge } from '../components/StatusBadge'
import { useCurrentEmployee } from '../context/CurrentEmployee'
import { formatNumber, mondayOf, toIsoDate } from '../lib/format'
import { useAsync } from '../lib/useAsync'
import type { Report } from '../types'

export default function ReportPage() {
  const { currentEmployeeId } = useCurrentEmployee()
  const employees = useAsync(listEmployees, [])
  const kpis = useAsync(listKpis, [])
  const tasks = useAsync(listTasks, [])
  const reports = useAsync(listReports, [])

  const [employeeId, setEmployeeId] = useState('')
  const [weekStart, setWeekStart] = useState(toIsoDate(mondayOf(new Date())))
  const [rawText, setRawText] = useState('')
  const [submitError, setSubmitError] = useState<unknown>(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<Report | null>(null)

  // Mặc định theo nhân viên đang chọn ở header, nhưng vẫn cho đổi tại chỗ.
  useEffect(() => {
    if (employeeId === '' && currentEmployeeId !== null) {
      setEmployeeId(String(currentEmployeeId))
    }
  }, [currentEmployeeId, employeeId])

  const kpiName = (id: number | null) =>
    id === null ? 'chưa gán' : (kpis.data ?? []).find((k) => k.id === id)?.name ?? `#${id}`
  const taskTitle = (id: number | null) =>
    id === null ? 'chưa gán' : (tasks.data ?? []).find((t) => t.id === id)?.title ?? `#${id}`

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSubmitError(null)
    setSubmitting(true)
    try {
      const report = await createReport({
        employee_id: Number(employeeId),
        week_start: weekStart,
        raw_text: rawText,
      })
      setResult(report)
      setRawText('')
      reports.reload()
    } catch (caught) {
      setSubmitError(caught)
    } finally {
      setSubmitting(false)
    }
  }

  async function reextract(id: number) {
    setSubmitError(null)
    try {
      setResult(await reextractReport(id))
      reports.reload()
    } catch (caught) {
      setSubmitError(caught)
    }
  }

  return (
    <div>
      <h1>Nộp báo cáo tuần</h1>
      <ErrorBox error={employees.error ?? reports.error} />

      <section className="card">
        <form onSubmit={submit}>
          <div className="form-grid">
            <label>
              Nhân viên
              <select
                data-testid="report-employee"
                required
                value={employeeId}
                onChange={(event) => setEmployeeId(event.target.value)}
              >
                <option value="">— chọn —</option>
                {(employees.data ?? []).map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tuần bắt đầu
              <input
                data-testid="report-week"
                type="date"
                required
                value={weekStart}
                onChange={(event) => setWeekStart(event.target.value)}
              />
            </label>
          </div>
          <label>
            Nội dung báo cáo
            <textarea
              data-testid="report-text"
              required
              value={rawText}
              placeholder="Mỗi việc một dòng. Ghi rõ tên KPI kèm con số, và các vướng mắc gặp phải."
              onChange={(event) => setRawText(event.target.value)}
            />
          </label>
          <button data-testid="report-submit" type="submit" disabled={submitting}>
            {submitting ? 'Đang trích xuất…' : 'Nộp báo cáo'}
          </button>
        </form>
        <ErrorBox error={submitError} />
      </section>

      {result !== null && (
        <section className="card" data-testid="report-result">
          <div className="row">
            <h2>
              Kết quả trích xuất — báo cáo #{result.id}, tuần {result.week_start}
            </h2>
            <ExtractionStatusBadge status={result.extraction_status} />
            <button
              type="button"
              className="secondary"
              data-testid="report-reextract"
              onClick={() => reextract(result.id)}
            >
              Trích lại
            </button>
          </div>

          {result.extraction_error !== null && (
            <ErrorBox error={new Error(result.extraction_error)} />
          )}

          <h2>Đề xuất cập nhật KPI</h2>
          {result.kpi_suggestions.length === 0 ? (
            <p className="muted">Không có đề xuất KPI nào.</p>
          ) : (
            <ul>
              {result.kpi_suggestions.map((suggestion) => (
                <li key={suggestion.id} data-testid="report-kpi-suggestion">
                  <strong>{kpiName(suggestion.suggested_kpi_id)}</strong>{' '}
                  {suggestion.suggested_delta >= 0 ? '+' : ''}
                  {formatNumber(suggestion.suggested_delta)} — “{suggestion.evidence}”
                </li>
              ))}
            </ul>
          )}

          <h2>Công việc báo là đã xong</h2>
          {result.task_suggestions.length === 0 ? (
            <p className="muted">Không có công việc nào.</p>
          ) : (
            <ul>
              {result.task_suggestions.map((suggestion) => (
                <li key={suggestion.id} data-testid="report-task-suggestion">
                  <strong>{taskTitle(suggestion.suggested_task_id)}</strong> — “
                  {suggestion.raw_text}”
                </li>
              ))}
            </ul>
          )}

          <h2>Vướng mắc</h2>
          {result.blockers.length === 0 ? (
            <p className="muted">Không có vướng mắc nào.</p>
          ) : (
            <ul>
              {result.blockers.map((blocker) => (
                <li key={blocker.id} data-testid="report-blocker">
                  {blocker.description}
                </li>
              ))}
            </ul>
          )}

          <p className="muted">
            Các đề xuất trên chưa làm đổi số liệu. Sang trang “Hàng đợi duyệt” để duyệt.
          </p>
        </section>
      )}

      <section className="card">
        <h2>Báo cáo gần đây</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Tuần</th>
              <th>Trạng thái</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(reports.data ?? []).slice(0, 10).map((report) => (
              <tr key={report.id}>
                <td>{report.id}</td>
                <td>{report.week_start}</td>
                <td>
                  <ExtractionStatusBadge status={report.extraction_status} />
                </td>
                <td>
                  <button type="button" className="secondary" onClick={() => setResult(report)}>
                    Xem
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(reports.data ?? []).length === 0 && <p className="muted">Chưa có báo cáo nào.</p>}
      </section>
    </div>
  )
}
```

- [ ] **Step 2: Kiểm tra kiểu và test hồi quy**

Chạy từ `frontend/`: `npx tsc --noEmit && npm test`
Kỳ vọng: không lỗi kiểu; test Vitest vẫn PASS.

- [ ] **Step 3: Kiểm tra thủ công trên trình duyệt**

Với backend và `npm run dev` đang chạy, mở `http://localhost:5173/report`:
- Nộp một báo cáo có dòng chứa tên KPI kèm số → panel kết quả hiện badge
  "Đã trích xuất" và ít nhất một đề xuất KPI.
- Nộp lại **đúng nhân viên và đúng tuần đó** → hộp lỗi hiện thông báo 409 về
  báo cáo đã tồn tại.
- Bấm "Trích lại" trên báo cáo vừa nộp → panel nạp lại, không lỗi.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ReportPage.tsx
git commit -m "feat(frontend): trang Nop bao cao"
```

---

### Task 6: Trang Hàng đợi duyệt

**Files:**
- Modify: `frontend/src/pages/ReviewPage.tsx` (thay hoàn toàn bản tạm từ Task 3)

**Interfaces:**
- Consumes: `useAsync`, `ErrorBox` (Task 3); `listSuggestions`/`listKpis`/`listTasks`/`approveKpiSuggestion`/`rejectKpiSuggestion`/`approveTaskSuggestion`/`rejectTaskSuggestion` (Task 2)
- Produces: `data-testid` của trang Hàng đợi duyệt

- [ ] **Step 1: Viết `frontend/src/pages/ReviewPage.tsx`**

```tsx
import { useState } from 'react'
import {
  approveKpiSuggestion,
  approveTaskSuggestion,
  listKpis,
  listSuggestions,
  listTasks,
  rejectKpiSuggestion,
  rejectTaskSuggestion,
} from '../api'
import { ErrorBox } from '../components/ErrorBox'
import { useAsync } from '../lib/useAsync'

/** Giá trị người dùng đang sửa trên một dòng, trước khi bấm Duyệt. */
interface KpiDraft {
  kpiId: string
  delta: string
  note: string
}

export default function ReviewPage() {
  const queue = useAsync(() => listSuggestions('pending'), [])
  const kpis = useAsync(listKpis, [])
  const tasks = useAsync(listTasks, [])

  const [kpiDrafts, setKpiDrafts] = useState<Record<number, KpiDraft>>({})
  const [taskDrafts, setTaskDrafts] = useState<Record<number, string>>({})
  const [actionError, setActionError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  const kpiUpdates = queue.data?.kpi_updates ?? []
  const taskCompletions = queue.data?.task_completions ?? []

  function kpiDraft(id: number, suggestedKpiId: number | null, suggestedDelta: number | null) {
    return (
      kpiDrafts[id] ?? {
        kpiId: suggestedKpiId === null ? '' : String(suggestedKpiId),
        delta: String(suggestedDelta ?? 0),
        note: '',
      }
    )
  }

  function patchKpiDraft(id: number, current: KpiDraft, patch: Partial<KpiDraft>) {
    setKpiDrafts((drafts) => ({ ...drafts, [id]: { ...current, ...patch } }))
  }

  /** Mọi thao tác duyệt/từ chối đi qua đây: cùng một cách xử lý lỗi và reload. */
  async function run(action: () => Promise<unknown>) {
    setActionError(null)
    setBusy(true)
    try {
      await action()
    } catch (caught) {
      // 409 nghĩa là ai đó đã xử lý dòng này trước. Vẫn reload để hàng đợi khớp thực tế.
      setActionError(caught)
    } finally {
      setBusy(false)
      setKpiDrafts({})
      setTaskDrafts({})
      queue.reload()
      tasks.reload()
    }
  }

  const isEmpty = kpiUpdates.length === 0 && taskCompletions.length === 0

  return (
    <div>
      <h1>Hàng đợi duyệt</h1>
      <ErrorBox error={queue.error} />
      <ErrorBox error={actionError} />

      {!queue.loading && isEmpty && (
        <p className="muted" data-testid="queue-empty">
          Không còn đề xuất nào đang chờ duyệt.
        </p>
      )}

      {kpiUpdates.length > 0 && (
        <section className="card">
          <h2>Đề xuất cập nhật KPI</h2>
          <table>
            <thead>
              <tr>
                <th>Nhân viên / tuần</th>
                <th>Căn cứ</th>
                <th>KPI</th>
                <th>Delta</th>
                <th>Ghi chú</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {kpiUpdates.map((row) => {
                const draft = kpiDraft(row.id, row.suggested_kpi_id, row.suggested_delta)
                return (
                  <tr key={row.id} data-testid="kpi-suggestion-row">
                    <td>
                      {row.employee_name}
                      <div className="muted">{row.week_start}</div>
                    </td>
                    <td>{row.evidence}</td>
                    <td>
                      <select
                        data-testid="kpi-row-select"
                        value={draft.kpiId}
                        onChange={(event) =>
                          patchKpiDraft(row.id, draft, { kpiId: event.target.value })
                        }
                      >
                        <option value="">— chọn KPI —</option>
                        {(kpis.data ?? []).map((kpi) => (
                          <option key={kpi.id} value={kpi.id}>
                            {kpi.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        data-testid="kpi-row-delta"
                        type="number"
                        step="any"
                        value={draft.delta}
                        onChange={(event) =>
                          patchKpiDraft(row.id, draft, { delta: event.target.value })
                        }
                      />
                    </td>
                    <td>
                      <input
                        data-testid="kpi-row-note"
                        value={draft.note}
                        onChange={(event) =>
                          patchKpiDraft(row.id, draft, { note: event.target.value })
                        }
                      />
                    </td>
                    <td className="row">
                      <button
                        type="button"
                        data-testid="kpi-row-approve"
                        // final_kpi_id bắt buộc khác null, nên chưa chọn KPI thì chưa duyệt được.
                        disabled={busy || draft.kpiId === '' || draft.delta.trim() === ''}
                        onClick={() =>
                          run(() =>
                            approveKpiSuggestion(row.id, {
                              final_kpi_id: Number(draft.kpiId),
                              final_delta: Number(draft.delta),
                              note: draft.note.trim() === '' ? null : draft.note.trim(),
                            }),
                          )
                        }
                      >
                        Duyệt
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        data-testid="kpi-row-reject"
                        disabled={busy}
                        onClick={() => run(() => rejectKpiSuggestion(row.id))}
                      >
                        Từ chối
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>
      )}

      {taskCompletions.length > 0 && (
        <section className="card">
          <h2>Công việc báo là đã xong</h2>
          <table>
            <thead>
              <tr>
                <th>Nhân viên / tuần</th>
                <th>Trích từ báo cáo</th>
                <th>Công việc</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {taskCompletions.map((row) => {
                const selected =
                  taskDrafts[row.id] ??
                  (row.suggested_task_id === null ? '' : String(row.suggested_task_id))
                return (
                  <tr key={row.id} data-testid="task-suggestion-row">
                    <td>
                      {row.employee_name}
                      <div className="muted">{row.week_start}</div>
                    </td>
                    <td>{row.raw_text}</td>
                    <td>
                      <select
                        data-testid="task-row-select"
                        value={selected}
                        onChange={(event) =>
                          setTaskDrafts((drafts) => ({ ...drafts, [row.id]: event.target.value }))
                        }
                      >
                        <option value="">— chọn công việc —</option>
                        {(tasks.data ?? []).map((task) => (
                          <option key={task.id} value={task.id}>
                            {task.title}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="row">
                      <button
                        type="button"
                        data-testid="task-row-approve"
                        disabled={busy || selected === ''}
                        onClick={() => run(() => approveTaskSuggestion(row.id, Number(selected)))}
                      >
                        Duyệt
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        data-testid="task-row-reject"
                        disabled={busy}
                        onClick={() => run(() => rejectTaskSuggestion(row.id))}
                      >
                        Từ chối
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Kiểm tra kiểu và test hồi quy**

Chạy từ `frontend/`: `npx tsc --noEmit && npm test`
Kỳ vọng: không lỗi kiểu; test Vitest vẫn PASS.

- [ ] **Step 3: Kiểm tra thủ công trên trình duyệt**

Với backend và frontend đang chạy, mở `http://localhost:5173/review`:
- Thấy các đề xuất từ báo cáo đã nộp ở Task 5, kèm tên nhân viên và tuần.
- Xoá trắng ô KPI trên một dòng → nút "Duyệt" chuyển sang mờ và bấm không được.
- Sửa delta rồi bấm "Duyệt" → dòng đó biến mất khỏi hàng đợi.
- Khi hàng đợi rỗng → hiện "Không còn đề xuất nào đang chờ duyệt."

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ReviewPage.tsx
git commit -m "feat(frontend): trang Hang doi duyet"
```

---

### Task 7: Trang Dashboard

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx` (thay hoàn toàn bản tạm từ Task 3)

**Interfaces:**
- Consumes: `useAsync`, `ErrorBox`, `KpiStatusBadge` (Task 3); `getDashboard`/`listReports` (Task 2); `barGeometry`/`formatNumber`/`formatPercent` (Task 1)
- Produces: `data-testid` của trang Dashboard

- [ ] **Step 1: Viết `frontend/src/pages/DashboardPage.tsx`**

```tsx
import { getDashboard, listReports } from '../api'
import { ErrorBox } from '../components/ErrorBox'
import { KpiStatusBadge } from '../components/StatusBadge'
import { barGeometry, formatNumber, formatPercent } from '../lib/format'
import { useAsync } from '../lib/useAsync'

/**
 * Số báo cáo gần nhất được quét để lấy vướng mắc.
 *
 * `GET /api/reports` trả về **mọi** báo cáo kèm toàn bộ `raw_text` và các
 * suggestion, đã sắp xếp `id DESC`. Blockers đi kèm sẵn trong cùng phản hồi nên
 * không có N+1, nhưng ta vẫn chỉ đọc phần đầu danh sách để phần hiển thị không
 * phình theo số báo cáo tích luỹ.
 */
const RECENT_REPORT_LIMIT = 5

export default function DashboardPage() {
  const dashboard = useAsync(getDashboard, [])
  const reports = useAsync(listReports, [])

  const items = dashboard.data ?? []
  const recentBlockers = (reports.data ?? [])
    .slice(0, RECENT_REPORT_LIMIT)
    .flatMap((report) =>
      report.blockers.map((blocker) => ({
        ...blocker,
        week_start: report.week_start,
      })),
    )

  return (
    <div>
      <h1>Dashboard</h1>
      <ErrorBox error={dashboard.error ?? reports.error} />

      {!dashboard.loading && items.length === 0 && (
        <p className="muted">Chưa có KPI nào. Sang trang “Thiết lập” để tạo.</p>
      )}

      <div className="kpi-grid">
        {items.map((item) => {
          const geometry = barGeometry(item.actual_value, item.target_value, item.expected_value)
          return (
            <section className="card" key={item.kpi_id} data-testid="kpi-card">
              <div className="kpi-card-top">
                <strong data-testid="kpi-card-name">{item.kpi_name}</strong>
                <KpiStatusBadge status={item.status} />
              </div>
              <div className="kpi-percent" data-testid="kpi-card-percent">
                {formatPercent(item.percent_complete)}
              </div>
              <div className="bar">
                <div
                  className={`bar-fill ${item.status}`}
                  style={{ width: `${geometry.fillPercent}%` }}
                />
                <div
                  className="bar-marker"
                  style={{ left: `${geometry.markerPercent}%` }}
                  title={`Kỳ vọng tới hôm nay: ${formatNumber(item.expected_value)} ${item.unit}`}
                />
              </div>
              <div data-testid="kpi-card-actual">
                {formatNumber(item.actual_value)} / {formatNumber(item.target_value)} {item.unit}
              </div>
              <div className="muted">
                Kỳ vọng tới hôm nay: {formatNumber(item.expected_value)} {item.unit}
              </div>
              <div className="muted">
                Phụ trách: {item.owner_name} · Kỳ: {item.period_start} → {item.period_end}
              </div>
            </section>
          )
        })}
      </div>

      <section className="card">
        <h2>Vướng mắc gần đây</h2>
        {recentBlockers.length === 0 ? (
          <p className="muted" data-testid="dashboard-no-blocker">
            Không có vướng mắc nào được ghi nhận.
          </p>
        ) : (
          <ul>
            {recentBlockers.map((blocker) => (
              <li key={blocker.id} data-testid="dashboard-blocker">
                {blocker.description} <span className="muted">(tuần {blocker.week_start})</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
```

- [ ] **Step 2: Kiểm tra kiểu, test và build**

Chạy từ `frontend/`: `npx tsc --noEmit && npm test && npm run build`
Kỳ vọng: không lỗi kiểu, test PASS, build thành công.

- [ ] **Step 3: Kiểm tra thủ công trên trình duyệt**

Mở `http://localhost:5173/dashboard`. Kỳ vọng:
- Mỗi KPI một thẻ, có phần trăm, thanh tiến độ, vạch mốc kỳ vọng, badge trạng thái.
- KPI đã duyệt ở Task 6 hiển thị đúng số đã cộng.
- Vướng mắc từ báo cáo ở Task 5 xuất hiện ở mục "Vướng mắc gần đây".

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(frontend): trang Dashboard"
```

---

### Task 8: Kiểm thử trọn vòng bằng Playwright

**Files:**
- Create: `tests/e2e/run_e2e.py`, `tests/e2e/full_flow.py`, `frontend/README.md`
- Modify: `README.md` (ở gốc repo)

**Interfaces:**
- Consumes: toàn bộ `data-testid` do Task 3–7 tạo ra; `.claude/skills/webapp-testing/scripts/with_server.py`
- Produces: lệnh `python tests/e2e/run_e2e.py` chạy được lặp lại nhiều lần

**Sử dụng skill:** Task này dùng skill `webapp-testing`. Đọc SKILL.md trước khi viết kịch bản.

- [ ] **Step 1: Cài Playwright vào `.venv` ở thư mục gốc repo**

Chạy từ thư mục gốc repo (`D:\projects\task-and-kpi`, **không** phải worktree —
`.venv` dùng chung):

```powershell
.venv\Scripts\python.exe -m pip install playwright
.venv\Scripts\python.exe -m playwright install chromium
```

Kỳ vọng: cài xong không lỗi; `playwright install` tải về Chromium.

- [ ] **Step 2: Viết `tests/e2e/run_e2e.py`**

```python
"""Chạy kịch bản e2e trọn vòng, lặp lại được nhiều lần.

Ba việc phải làm trước khi giao cho `with_server.py`:

1. Xoá file SQLite tạm, để mỗi lần chạy bắt đầu từ database trống.
2. Giải phóng cổng 8000 và 5173. `with_server.py` spawn server bằng
   `shell=True` và khi dọn dẹp chỉ `terminate()` chính tiến trình đó — trên
   Windows đó là `cmd.exe` bọc ngoài, nên `node.exe` và `python.exe` con sống
   sót và tiếp tục giữ cổng. Không dọn thì lần chạy thứ hai chết ở
   "Server failed to start".
3. Đặt DATABASE_URL và LLM_PROVIDER cho tiến trình con.

Về `npm` trên Windows: `with_server.py` dùng `shell=True`, nên lệnh chạy qua
`cmd.exe /c` và `npm` được phân giải thành `npm.cmd` mà không cần gọi tường
minh. Dùng `cd /d` (có `/d`) để chuyển được cả ổ đĩa. `subprocess.run(..., env=env)`
ở dưới truyền env xuống `with_server.py`, và `with_server.py` spawn con bằng
`Popen` không đặt `env=`, nên hai server đều thừa hưởng DATABASE_URL.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
DB_PATH = BACKEND_DIR / ".e2e" / "kpi_e2e.db"
WITH_SERVER = REPO_ROOT / ".claude" / "skills" / "webapp-testing" / "scripts" / "with_server.py"
FLOW_SCRIPT = pathlib.Path(__file__).resolve().parent / "full_flow.py"
PORTS = (8000, 5173)


def pids_listening_on(port: int) -> set[str]:
    """PID của các tiến trình đang LISTEN trên `port` (chỉ Windows)."""
    if sys.platform != "win32":
        return set()
    result = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True
    )
    pids: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        # Proto | Local Address | Foreign Address | State | PID
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
            pids.add(parts[4])
    return pids


def free_ports() -> None:
    for port in PORTS:
        for pid in pids_listening_on(port):
            print(f"Giải phóng cổng {port}: taskkill PID {pid}")
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", pid], capture_output=True
            )


def main() -> int:
    free_ports()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)

    env = dict(os.environ)
    # Biến môi trường có độ ưu tiên cao hơn file backend/.env trong
    # pydantic-settings, nên không cần sửa gì trong backend.
    env["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
    env["LLM_PROVIDER"] = "mock"

    backend_cmd = (
        f'cd /d "{BACKEND_DIR}" && '
        f'"{sys.executable}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000'
    )
    frontend_cmd = f'cd /d "{FRONTEND_DIR}" && npm run dev'

    command = [
        sys.executable,
        str(WITH_SERVER),
        "--server", backend_cmd, "--port", "8000",
        "--server", frontend_cmd, "--port", "5173",
        "--timeout", "90",
        "--", sys.executable, str(FLOW_SCRIPT),
    ]

    try:
        return subprocess.run(command, env=env).returncode
    finally:
        free_ports()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Viết `tests/e2e/full_flow.py`**

```python
"""Kịch bản trọn vòng: tạo dữ liệu → nộp báo cáo → duyệt → dashboard đổi số.

Server do `run_e2e.py` khởi động sẵn. Luôn mở frontend qua `localhost:5173`,
không dùng `127.0.0.1` — backend chỉ mở CORS cho đúng origin đó.
"""

from __future__ import annotations

import datetime as dt

from playwright.sync_api import expect, sync_playwright

BASE_URL = "http://localhost:5173"

KPI_NAME = "Doanh so"
TASK_TITLE = "Goi khach hang moi"
EMPLOYEE_NAME = "Le Van A"
EMPLOYEE_EMAIL = "levana@example.com"

# Kỳ đã trôi qua phần lớn: expected xấp xỉ 86% của chỉ tiêu, nên actual = 0
# chắc chắn rơi vào "Có nguy cơ" theo ngưỡng 0.8 trong rules.py.
TODAY = dt.date.today()
PERIOD_START = (TODAY - dt.timedelta(days=60)).isoformat()
PERIOD_END = (TODAY + dt.timedelta(days=10)).isoformat()
WEEK_START = (TODAY - dt.timedelta(days=TODAY.weekday())).isoformat()

# MockProvider khớp tên KPI / tiêu đề task trong từng dòng và lấy **số đầu tiên
# trên dòng** làm delta, nên dòng đầu phải có 40 là con số đầu tiên.
REPORT_TEXT = "\n".join(
    [
        f"{KPI_NAME} tang them 40 trieu trong tuan nay",
        f"{TASK_TITLE} da hoan thanh",
        "Vuong mac: thieu du lieu tu phong ke toan",
    ]
)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda message: print(f"[console:{message.type}] {message.text}"))

        try:
            # --- Thiết lập: nhân viên, KPI, công việc -------------------------
            page.goto(f"{BASE_URL}/setup")
            page.wait_for_load_state("networkidle")

            page.get_by_test_id("employee-form-name").fill(EMPLOYEE_NAME)
            page.get_by_test_id("employee-form-email").fill(EMPLOYEE_EMAIL)
            page.get_by_test_id("employee-form-submit").click()
            expect(page.get_by_test_id("employee-row")).to_have_count(1)

            page.get_by_test_id("kpi-form-name").fill(KPI_NAME)
            page.get_by_test_id("kpi-form-target").fill("100")
            page.get_by_test_id("kpi-form-unit").fill("trieu")
            page.get_by_test_id("kpi-form-owner").select_option(label=EMPLOYEE_NAME)
            page.get_by_test_id("kpi-form-start").fill(PERIOD_START)
            page.get_by_test_id("kpi-form-end").fill(PERIOD_END)
            page.get_by_test_id("kpi-form-submit").click()
            expect(page.get_by_test_id("kpi-row")).to_have_count(1)

            page.get_by_test_id("task-form-title").fill(TASK_TITLE)
            page.get_by_test_id("task-form-kpi").select_option(label=KPI_NAME)
            page.get_by_test_id("task-form-assignee").select_option(label=EMPLOYEE_NAME)
            page.get_by_test_id("task-form-submit").click()
            expect(page.get_by_test_id("task-row")).to_have_count(1)
            print("OK  Thiet lap: tao nhan vien, KPI, cong viec")

            # --- Dashboard trước khi duyệt: phải đang cảnh báo ----------------
            # Không kiểm bước này thì bước tắt cảnh báo ở cuối không chứng minh
            # được điều gì.
            page.goto(f"{BASE_URL}/dashboard")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_test_id("kpi-card")).to_have_count(1)
            # percent_complete = actual/target = 0/100 = 0.0, và formatPercent nhân
            # 100 (thang phân số được test_rules.py:90/101 chốt), nên đúng "0%".
            expect(page.get_by_test_id("kpi-card-percent")).to_have_text("0%")
            expect(page.get_by_test_id("kpi-card-actual")).to_have_text("0 / 100 trieu")
            expect(page.get_by_test_id("kpi-card-status")).to_have_text("Có nguy cơ")
            print("OK  Dashboard truoc khi duyet: 0%, 0/100, Co nguy co")

            # --- Nộp báo cáo ---------------------------------------------------
            page.goto(f"{BASE_URL}/report")
            page.wait_for_load_state("networkidle")
            page.get_by_test_id("report-employee").select_option(label=EMPLOYEE_NAME)
            page.get_by_test_id("report-week").fill(WEEK_START)
            page.get_by_test_id("report-text").fill(REPORT_TEXT)
            page.get_by_test_id("report-submit").click()

            expect(page.get_by_test_id("report-result")).to_be_visible()
            expect(page.get_by_test_id("report-status-badge").first).to_have_text("Đã trích xuất")
            expect(page.get_by_test_id("report-kpi-suggestion")).to_have_count(1)
            expect(page.get_by_test_id("report-task-suggestion")).to_have_count(1)
            expect(page.get_by_test_id("report-blocker")).to_have_count(1)
            print("OK  Nop bao cao: 1 de xuat KPI, 1 cong viec, 1 vuong mac")

            # --- Duyệt, có sửa số liệu ------------------------------------------
            page.goto(f"{BASE_URL}/review")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_test_id("kpi-suggestion-row")).to_have_count(1)
            expect(page.get_by_test_id("task-suggestion-row")).to_have_count(1)

            # Sửa delta 40 → 100 để kiểm luôn đường final_* chứ không phải suggested_*.
            page.get_by_test_id("kpi-row-delta").fill("100")
            page.get_by_test_id("kpi-row-note").fill("Da doi chieu voi ke toan")
            page.get_by_test_id("kpi-row-approve").click()
            expect(page.get_by_test_id("kpi-suggestion-row")).to_have_count(0)

            page.get_by_test_id("task-row-approve").click()
            expect(page.get_by_test_id("queue-empty")).to_be_visible()
            print("OK  Duyet: sua delta thanh 100 va duyet ca hai de xuat")

            # --- Dashboard sau khi duyệt: đổi số và tắt cảnh báo ----------------
            page.goto(f"{BASE_URL}/dashboard")
            page.wait_for_load_state("networkidle")
            # actual/target = 100/100 = 1.0 → "100%". Đây chính là ca mà
            # test_rules.py:90 khẳng định percent_complete == 1.0.
            expect(page.get_by_test_id("kpi-card-percent")).to_have_text("100%")
            expect(page.get_by_test_id("kpi-card-actual")).to_have_text("100 / 100 trieu")
            expect(page.get_by_test_id("kpi-card-status")).to_have_text("Hoàn thành")
            # Cảnh báo đã tắt: không còn thẻ nào mang nhãn "Có nguy cơ".
            expect(page.get_by_text("Có nguy cơ")).to_have_count(0)
            expect(page.get_by_test_id("dashboard-blocker")).to_have_count(1)
            print("OK  Dashboard sau khi duyet: 100%, 100/100, Hoan thanh, canh bao da tat")

            page.screenshot(path="tests/e2e/dashboard-sau-khi-duyet.png", full_page=True)
            print("\nTRON VONG THANH CONG")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Chạy e2e lần thứ nhất**

Chạy từ thư mục gốc của **worktree**:

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe tests\e2e\run_e2e.py
```

Kỳ vọng: in ra lần lượt năm dòng `OK ...` rồi `TRON VONG THANH CONG`, thoát mã 0.

Nếu thất bại, **dừng lại và dùng skill `superpowers:systematic-debugging`** trước
khi sửa bất cứ thứ gì. Không được sửa `backend/` để làm test qua.

- [ ] **Step 5: Chạy e2e lần thứ hai ngay sau đó — đây là phép thử thật sự**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe tests\e2e\run_e2e.py
```

Kỳ vọng: kết quả **y hệt** lần một. Lần chạy này chứng minh hai điều mà lần một
không chứng minh được: DB tạm được tạo mới thật, và cổng 8000/5173 đã được giải
phóng thật sau lần trước. Nếu lần hai chết ở "Server failed to start", nghĩa là
`free_ports()` chưa đủ — sửa `run_e2e.py`, không sửa `with_server.py`.

- [ ] **Step 6: Viết `frontend/README.md`**

```markdown
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
```

- [ ] **Step 7: Cập nhật `README.md` ở gốc repo**

Thêm mục frontend vào README gốc, giữ nguyên phần backend đã có. Đọc file hiện
tại trước, rồi chèn một mục mới:

```markdown
## Frontend

React + Vite + TypeScript, bốn trang: Thiết lập, Nộp báo cáo, Hàng đợi duyệt,
Dashboard. Xem `frontend/README.md`.

```powershell
cd frontend
npm install
npm run dev     # http://localhost:5173
```

## Kiểm thử trọn vòng

```powershell
.venv\Scripts\python.exe tests\e2e\run_e2e.py
```
```

- [ ] **Step 8: Xác minh lần cuối toàn bộ**

Chạy từ `frontend/`: `npm test && npx tsc --noEmit && npm run build`
Kỳ vọng: PASS / không lỗi / build thành công.

Chạy từ `backend/`: `D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest -q`
Kỳ vọng: **129 passed** — đúng như trước khi bắt đầu giai đoạn 2, chứng minh
backend không bị đụng vào.

Chạy: `git status --short`
Kỳ vọng: không có file `.db`, `node_modules/`, hay `dist/` bị theo dõi.

- [ ] **Step 9: Commit**

```bash
git add tests/e2e frontend/README.md README.md
git commit -m "test(e2e): kich ban tron vong bang Playwright, chay lai duoc"
```

---

## Self-Review

**Spec coverage** — đối chiếu từng mục của spec giai đoạn 2:

| Mục spec | Task |
|---|---|
| §5 bố cục file | Task 1–8 |
| §6 `api.ts` + `ApiError` + `status = 0` | Task 2 |
| §7 bốn hàm thuần | Task 1 |
| §8 trang Thiết lập | Task 4 |
| §8 trang Nộp báo cáo (409, `failed`, trích lại) | Task 5 |
| §8 trang Hàng đợi duyệt (hai bảng, sửa tại dòng, chặn khi thiếu KPI) | Task 6 |
| §8 trang Dashboard (thanh tiến độ, mốc kỳ vọng, blockers 5 báo cáo gần nhất) | Task 7 |
| §9 Vitest | Task 1 (format), Task 2 (api) |
| §9 Playwright trọn vòng, gồm bước kiểm "Có nguy cơ" trước khi duyệt | Task 8 |
| §9 chạy lặp lại được: DB tạm, dọn cổng, localStorage | Task 8 Step 2, 4, 5 |
| §3 `strictPort`, `localhost:5173`, không N+1 blockers | Task 1 Step 2, Task 8, Task 7 |
| Không sửa backend | Global Constraints + Task 8 Step 8 |

**Placeholder scan** — không còn "TBD"/"TODO"/"tương tự Task N". Mọi bước có mã
đều kèm mã đầy đủ.

**Type consistency** — `useAsync` trả `{ data, error, loading, reload }` và được
dùng đúng tên đó ở cả bốn trang. `ApiError.status` dùng nhất quán ở `ErrorBox` và
`api.test.ts`. `formatPercent` nhận phân số ở cả định nghĩa (Task 1) lẫn nơi dùng
(Task 7). `data-testid` trong bảng quy ước khớp với Task 3–7 và với Task 8.
