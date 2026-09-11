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
