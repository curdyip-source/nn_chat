import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

type LayoutState = {
  sidebarHidden: boolean
  setSidebarHidden: (hidden: boolean) => void
}

const LayoutCtx = createContext<LayoutState | null>(null)

export function LayoutProvider({ children }: { children: ReactNode }) {
  const [sidebarHidden, setSidebarHidden] = useState(false)
  const value = useMemo(() => ({ sidebarHidden, setSidebarHidden }), [sidebarHidden])
  return <LayoutCtx.Provider value={value}>{children}</LayoutCtx.Provider>
}

export function useLayout(): LayoutState {
  const ctx = useContext(LayoutCtx)
  if (!ctx) throw new Error('useLayout вне LayoutProvider')
  return ctx
}
