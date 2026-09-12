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
