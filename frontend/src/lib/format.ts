/** Hàm thuần dùng chung. Không chạm DOM, không chạm mạng. */

const UNKNOWN_ERROR = 'Đã xảy ra lỗi không xác định.'

interface PydanticError {
  loc?: unknown
  msg?: unknown
}

/**
 * Backend trả `detail` ở hai dạng: chuỗi (từ các exception handler nghiệp vụ)
 * và mảng lỗi Pydantic (từ RequestValidationError). Hàm này đưa cả hai — cùng
 * mọi dạng lạ khác — về đúng một câu hiển thị được.
 */
export function detailToMessage(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail.trim() === '' ? UNKNOWN_ERROR : detail
  }

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item.trim()
        if (item === null || typeof item !== 'object') return ''
        const entry = item as PydanticError
        const message = typeof entry.msg === 'string' ? entry.msg : ''
        const field = Array.isArray(entry.loc)
          ? entry.loc.filter((part) => part !== 'body').join('.')
          : ''
        if (message === '') return ''
        return field === '' ? message : `${field}: ${message}`
      })
      .filter((part) => part !== '')
    if (parts.length > 0) return parts.join('; ')
  }

  return UNKNOWN_ERROR
}

export function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min
  return Math.min(max, Math.max(min, value))
}

/**
 * Hình học thanh tiến độ. Khác với phần trăm hiển thị, hai số này **phải** kẹp
 * trong 0–100, nếu không thanh sẽ tràn ra khỏi khung.
 */
export function barGeometry(
  actual: number,
  target: number,
  expected: number,
): { fillPercent: number; markerPercent: number } {
  if (!(target > 0)) return { fillPercent: 0, markerPercent: 0 }
  return {
    fillPercent: clamp((actual / target) * 100, 0, 100),
    markerPercent: clamp((expected / target) * 100, 0, 100),
  }
}

/** Nhận **phân số** (backend trả `actual / target`), trả chuỗi phần trăm. */
export function formatPercent(fraction: number): string {
  if (!Number.isFinite(fraction)) return '0%'
  return `${formatNumber(Math.round(fraction * 1000) / 10)}%`
}

export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return '0'
  return String(Math.round(value * 100) / 100)
}

/** Đưa một ngày về thứ Hai cùng tuần. Chủ nhật thuộc về tuần vừa qua. */
export function mondayOf(value: Date): Date {
  const result = new Date(value.getFullYear(), value.getMonth(), value.getDate())
  const weekday = result.getDay() // 0 = Chủ nhật
  result.setDate(result.getDate() + (weekday === 0 ? -6 : 1 - weekday))
  return result
}

/**
 * `yyyy-mm-dd` theo giờ **địa phương**. Không dùng `toISOString()`: ở múi giờ
 * dương nó quy đổi nửa đêm địa phương về ngày hôm trước theo UTC, và ô `week_start`
 * sẽ lệch một ngày.
 */
export function toIsoDate(value: Date): string {
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${value.getFullYear()}-${month}-${day}`
}
