import { describe, it, expect } from 'vitest'
import {
  barGeometry,
  clamp,
  detailToMessage,
  formatNumber,
  formatPercent,
  mondayOf,
  toIsoDate,
} from './format'

describe('detailToMessage', () => {
  it('trả nguyên chuỗi khi backend gửi detail dạng chuỗi', () => {
    expect(detailToMessage('Không tìm thấy báo cáo 7')).toBe('Không tìm thấy báo cáo 7')
  })

  it('ghép mảng lỗi Pydantic thành một câu, bỏ tiền tố "body"', () => {
    const detail = [
      { loc: ['body', 'target_value'], msg: 'Input should be greater than 0', type: 'greater_than' },
      { loc: ['body', 'unit'], msg: 'Field required', type: 'missing' },
    ]
    expect(detailToMessage(detail)).toBe(
      'target_value: Input should be greater than 0; unit: Field required',
    )
  })

  it('có câu dự phòng khi detail là undefined', () => {
    expect(detailToMessage(undefined)).toBe('Đã xảy ra lỗi không xác định.')
  })

  it('có câu dự phòng khi detail là một object lạ', () => {
    expect(detailToMessage({ weird: true })).toBe('Đã xảy ra lỗi không xác định.')
  })

  it('coi chuỗi rỗng như không có thông tin', () => {
    expect(detailToMessage('   ')).toBe('Đã xảy ra lỗi không xác định.')
  })
})

describe('clamp', () => {
  it('kẹp hai đầu', () => {
    expect(clamp(-5, 0, 100)).toBe(0)
    expect(clamp(150, 0, 100)).toBe(100)
    expect(clamp(42, 0, 100)).toBe(42)
  })

  it('trả min khi giá trị không hữu hạn', () => {
    expect(clamp(Number.NaN, 0, 100)).toBe(0)
    expect(clamp(Number.POSITIVE_INFINITY, 0, 100)).toBe(0)
  })
})

describe('barGeometry', () => {
  it('tính phần trăm lấp đầy và vị trí mốc kỳ vọng', () => {
    expect(barGeometry(40, 100, 85)).toEqual({ fillPercent: 40, markerPercent: 85 })
  })

  it('kẹp phần lấp đầy về 100 khi vượt chỉ tiêu', () => {
    expect(barGeometry(150, 100, 100)).toEqual({ fillPercent: 100, markerPercent: 100 })
  })

  it('trả 0 khi target không dương, thay vì chia cho 0', () => {
    expect(barGeometry(10, 0, 5)).toEqual({ fillPercent: 0, markerPercent: 0 })
  })
})

describe('formatPercent', () => {
  it('nhận phân số và trả về số phần trăm', () => {
    // backend trả percent_complete = actual / target, tức 0.4 nghĩa là 40%
    expect(formatPercent(0.4)).toBe('40%')
  })

  it('làm tròn tới một chữ số thập phân', () => {
    expect(formatPercent(0.8571)).toBe('85.7%')
  })

  it('không kẹp trên 100%', () => {
    expect(formatPercent(1.2)).toBe('120%')
  })
})

describe('formatNumber', () => {
  it('bỏ phần thập phân thừa', () => {
    expect(formatNumber(100)).toBe('100')
    expect(formatNumber(40.5)).toBe('40.5')
  })
})

describe('mondayOf', () => {
  it('giữ nguyên khi đã là thứ Hai', () => {
    // 2026-09-07 là thứ Hai
    expect(toIsoDate(mondayOf(new Date(2026, 8, 7)))).toBe('2026-09-07')
  })

  it('lùi về thứ Hai đầu tuần khi ở giữa tuần', () => {
    // 2026-09-11 là thứ Sáu
    expect(toIsoDate(mondayOf(new Date(2026, 8, 11)))).toBe('2026-09-07')
  })

  it('coi Chủ nhật là cuối tuần đó, không phải đầu tuần sau', () => {
    // 2026-09-13 là Chủ nhật
    expect(toIsoDate(mondayOf(new Date(2026, 8, 13)))).toBe('2026-09-07')
  })
})

describe('toIsoDate', () => {
  it('dùng giờ địa phương, không lệch ngày như toISOString', () => {
    // Ở múi giờ UTC+7, new Date(2026, 8, 11).toISOString() cho "2026-09-10T17:00:00Z"
    // — lùi mất một ngày. toIsoDate phải miễn nhiễm với chuyện đó.
    expect(toIsoDate(new Date(2026, 8, 11))).toBe('2026-09-11')
  })
})
