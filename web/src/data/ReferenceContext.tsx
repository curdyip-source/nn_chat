import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { fetchReferenceData } from '../api/endpoints'
import type { Currency, ReferenceData, Status } from '../api/types'

type RefState = ReferenceData & {
  loading: boolean
  error: string | null
  reload: () => void
  statusesByType: (type: string) => Status[]
  defaultCurrency: Currency | null
}

const empty: ReferenceData = {
  establishments: [],
  order_methods: [],
  sales_channels: [],
  statuses: [],
  currencies: [],
}

const RefCtx = createContext<RefState | null>(null)

export function ReferenceProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<ReferenceData>(empty)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchReferenceData()
      .then((res) => {
        if (cancelled) return
        setData(res)
        setError(null)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Ошибка загрузки справочников')
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [tick])

  const value: RefState = {
    ...data,
    loading,
    error,
    reload: () => setTick((t) => t + 1),
    statusesByType: (type) => data.statuses.filter((s) => s.status_type === type),
    defaultCurrency: data.currencies[0] ?? null,
  }

  return <RefCtx.Provider value={value}>{children}</RefCtx.Provider>
}

export function useReference(): RefState {
  const ctx = useContext(RefCtx)
  if (!ctx) throw new Error('useReference вне ReferenceProvider')
  return ctx
}
