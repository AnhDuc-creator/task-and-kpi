import { describe, it, expect, afterEach, vi } from 'vitest'
import { ApiError, createEmployee, getDashboard, listEmployees } from '../api'

function mockFetch(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const stub = vi.fn().mockResolvedValue(response as Response)
  vi.stubGlobal('fetch', stub)
  return stub
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('request thành công', () => {
  it('trả về JSON đã parse', async () => {
    mockFetch({ ok: true, status: 200, json: async () => [{ id: 1, name: 'An', email: 'a@b.c' }] })
    await expect(listEmployees()).resolves.toEqual([{ id: 1, name: 'An', email: 'a@b.c' }])
  })

  it('gửi Content-Type json kèm body khi POST', async () => {
    const stub = mockFetch({ ok: true, status: 201, json: async () => ({ id: 1 }) })
    await createEmployee({ name: 'An', email: 'a@b.c' })
    const init = stub.mock.calls[0][1] as RequestInit
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    expect(init.body).toBe(JSON.stringify({ name: 'An', email: 'a@b.c' }))
  })
})

describe('lỗi HTTP', () => {
  it('409 ném ApiError mang đúng status và thông điệp từ detail chuỗi', async () => {
    mockFetch({ ok: false, status: 409, json: async () => ({ detail: 'Email a@b.c đã được dùng' }) })
    const error = await createEmployee({ name: 'An', email: 'a@b.c' }).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
    expect(error.message).toBe('Email a@b.c đã được dùng')
  })

  it('404 ném ApiError với status 404', async () => {
    mockFetch({ ok: false, status: 404, json: async () => ({ detail: 'Không tìm thấy KPI 9' }) })
    const error = await getDashboard().catch((e) => e)
    expect(error.status).toBe(404)
  })

  it('422 ghép mảng lỗi Pydantic thành một câu', async () => {
    mockFetch({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [{ loc: ['body', 'target_value'], msg: 'Input should be greater than 0' }],
      }),
    })
    const error = await getDashboard().catch((e) => e)
    expect(error.status).toBe(422)
    expect(error.message).toBe('target_value: Input should be greater than 0')
  })

  it('không sập khi thân phản hồi lỗi không phải JSON', async () => {
    mockFetch({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => {
        throw new Error('not json')
      },
    })
    const error = await getDashboard().catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(500)
  })
})

describe('lỗi mạng', () => {
  it('cho status 0 để UI phân biệt được "backend chưa bật"', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const error = await getDashboard().catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(0)
    expect(error.message).toContain('backend')
  })
})
