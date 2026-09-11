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
