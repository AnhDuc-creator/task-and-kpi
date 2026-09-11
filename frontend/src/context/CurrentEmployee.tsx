import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

const STORAGE_KEY = 'kpi.currentEmployeeId'

interface CurrentEmployeeValue {
  currentEmployeeId: number | null
  setCurrentEmployeeId: (id: number | null) => void
}

const CurrentEmployeeContext = createContext<CurrentEmployeeValue>({
  currentEmployeeId: null,
  setCurrentEmployeeId: () => undefined,
})

function readStored(): number | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw === null) return null
    const parsed = Number(raw)
    return Number.isInteger(parsed) ? parsed : null
  } catch {
    // localStorage có thể bị chặn (cửa sổ ẩn danh, thiết lập trình duyệt).
    return null
  }
}

export function CurrentEmployeeProvider({ children }: { children: ReactNode }) {
  const [currentEmployeeId, setState] = useState<number | null>(readStored)

  useEffect(() => {
    try {
      if (currentEmployeeId === null) window.localStorage.removeItem(STORAGE_KEY)
      else window.localStorage.setItem(STORAGE_KEY, String(currentEmployeeId))
    } catch {
      // Không nhớ được thì thôi, không phải lỗi chặn người dùng.
    }
  }, [currentEmployeeId])

  const setCurrentEmployeeId = useCallback((id: number | null) => setState(id), [])

  return (
    <CurrentEmployeeContext.Provider value={{ currentEmployeeId, setCurrentEmployeeId }}>
      {children}
    </CurrentEmployeeContext.Provider>
  )
}

export function useCurrentEmployee(): CurrentEmployeeValue {
  return useContext(CurrentEmployeeContext)
}
