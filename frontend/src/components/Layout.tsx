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
