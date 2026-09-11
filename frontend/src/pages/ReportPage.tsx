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
