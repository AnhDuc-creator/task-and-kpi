import { ApiError } from '../api'

export function ErrorBox({ error }: { error: unknown }) {
  if (error === null || error === undefined) return null

  const message = error instanceof Error ? error.message : String(error)
  const hint =
    error instanceof ApiError && error.status === 0
      ? 'Chạy `uvicorn app.main:app --reload` trong thư mục backend rồi thử lại.'
      : null

  return (
    <div className="error-box" data-testid="error-box" role="alert">
      <strong>Lỗi:</strong> {message}
      {hint !== null && <div className="error-hint">{hint}</div>}
    </div>
  )
}
