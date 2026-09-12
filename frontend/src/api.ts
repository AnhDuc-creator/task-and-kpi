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
