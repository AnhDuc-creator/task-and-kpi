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
