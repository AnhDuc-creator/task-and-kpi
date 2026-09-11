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
