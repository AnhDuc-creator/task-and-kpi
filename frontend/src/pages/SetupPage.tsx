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

  const employeeNameById = (id: number) =>
    employeeList.find((item) => item.id === id)?.name ?? `#${id}`
  const kpiNameById = (id: number) => kpiList.find((item) => item.id === id)?.name ?? `#${id}`

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
                <td>{employeeNameById(kpi.owner_id)}</td>
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
                <td>{kpiNameById(task.kpi_id)}</td>
                <td>{employeeNameById(task.assignee_id)}</td>
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
