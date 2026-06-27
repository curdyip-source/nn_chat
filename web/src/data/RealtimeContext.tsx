import { createContext, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { streamEvents, UnauthorizedError } from '../api/client'
import type { MessageStreamEvent } from '../api/types'

// One app-wide SSE connection to /messages/stream. Pages read `revision` (a debounced counter
// that bumps on any realtime change) to refetch, and `lastEvent` for surgical handling (e.g.
// removing a deleted chat message). Since every order/inventory/registration has a chat card,
// the message stream carries every entity change — one channel keeps the whole UI fresh.
type RealtimeState = { revision: number; lastEvent: MessageStreamEvent | null }

const RealtimeCtx = createContext<RealtimeState>({ revision: 0, lastEvent: null })

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<RealtimeState>({ revision: 0, lastEvent: null })
  const revisionRef = useRef(0)
  const debounceRef = useRef<number | null>(null)

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()

    const bumpRevisionDebounced = () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
      debounceRef.current = window.setTimeout(() => {
        revisionRef.current += 1
        setState((prev) => ({ revision: revisionRef.current, lastEvent: prev.lastEvent }))
      }, 400)
    }

    const run = async () => {
      while (!cancelled) {
        try {
          await streamEvents((event) => {
            setState((prev) => ({ revision: prev.revision, lastEvent: event as MessageStreamEvent }))
            bumpRevisionDebounced()
          }, controller.signal)
        } catch (err) {
          // Session expired — page requests will trigger logout; stop reconnecting.
          if (err instanceof UnauthorizedError) break
          // Otherwise it was a dropped connection / abort; fall through to reconnect.
        }
        if (cancelled) break
        await new Promise((resolve) => setTimeout(resolve, 3000))
      }
    }

    void run()

    return () => {
      cancelled = true
      controller.abort()
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [])

  return <RealtimeCtx.Provider value={state}>{children}</RealtimeCtx.Provider>
}

export function useRealtime(): RealtimeState {
  return useContext(RealtimeCtx)
}
