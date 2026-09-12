import { useLocation } from 'react-router-dom'
import { listEmployees } from '../api'
import { useCurrentEmployee } from '../context/CurrentEmployee'
import { useAsync } from '../lib/useAsync'

export function EmployeePicker() {
  const { currentEmployeeId, setCurrentEmployeeId } = useCurrentEmployee()
  // Layout (nơi component này sống) được React Router giữ mounted xuyên suốt
  // điều hướng, nên nếu không có pathname trong deps thì danh sách nhân viên
  // chỉ được nạp một lần cho cả phiên — tạo nhân viên mới ở trang Setup rồi
  // mở dropdown này sẽ không thấy, phải F5 mới ra.
  const { pathname } = useLocation()
  const { data: employees } = useAsync(listEmployees, [pathname])

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
