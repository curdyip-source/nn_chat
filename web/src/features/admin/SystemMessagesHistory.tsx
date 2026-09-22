import { useEffect, useState } from 'react'
import { getSystemMessageReceipts, listSystemMessages } from '../../api/endpoints'
import type { SystemMessage, SystemMessageReceipt } from '../../api/types'
import { useRealtime } from '../../data/RealtimeContext'

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Содержимое оверлея «История системных сообщений» (открывается модалкой из
// AdminPage — так же, как «История заказа»). Сам себе тянет realtime: и на
// отправку нового сообщения, и на каждое подтверждение прочтения сервер шлёт
// SSE-сигнал, useRealtime даёт revision + фолбэк-поллинг раз в 5с на случай,
// если SSE не дошёл.
export function SystemMessagesHistory() {
  const { revision } = useRealtime()
  const [messages, setMessages] = useState<SystemMessage[]>([])
  const [loaded, setLoaded] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [receipts, setReceipts] = useState<Record<number, SystemMessageReceipt[]>>({})
  const [receiptsLoadingId, setReceiptsLoadingId] = useState<number | null>(null)

  useEffect(() => {
    let alive = true
    listSystemMessages()
      .then(({ items }) => {
        if (alive) {
          setMessages(items)
          setLoaded(true)
        }
      })
      .catch(() => {
        if (alive) setLoaded(true)
      })
    return () => {
      alive = false
    }
  }, [revision])

  useEffect(() => {
    if (expandedId === null) return
    let alive = true
    setReceiptsLoadingId(expandedId)
    getSystemMessageReceipts(expandedId)
      .then((r) => {
        if (alive) setReceipts((prev) => ({ ...prev, [expandedId]: r.items }))
      })
      .finally(() => {
        if (alive) setReceiptsLoadingId(null)
      })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandedId, revision])

  const toggle = (id: number) => setExpandedId((prev) => (prev === id ? null : id))

  if (!loaded) {
    return <div style={{ fontSize: 13.5, color: 'var(--text-dim)' }}>Загрузка…</div>
  }

  if (messages.length === 0) {
    return <div style={{ fontSize: 13.5, color: 'var(--text-dim)' }}>Сообщений ещё не отправляли.</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {messages.map((m) => (
        <div key={m.id} style={{ border: '1px solid var(--border, #e5e7eb)', borderRadius: 12, padding: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 4 }}>
                {formatDateTime(m.created_at)} · {m.created_by?.name ?? '—'}
                {m.important && <span style={{ marginLeft: 8, color: '#b45309', fontWeight: 600 }}>Важное</span>}
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.4, whiteSpace: 'pre-wrap' }}>{m.text}</div>
            </div>
            <button
              type="button"
              onClick={() => toggle(m.id)}
              style={{
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                color: 'var(--accent, #2563eb)',
                fontSize: 13,
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
            >
              {m.read_count} из {m.recipients_count} прочитали {expandedId === m.id ? '▲' : '▼'}
            </button>
          </div>

          {expandedId === m.id && (
            <div style={{ marginTop: 10, borderTop: '1px solid var(--border, #e5e7eb)', paddingTop: 10 }}>
              {receiptsLoadingId === m.id && !receipts[m.id] && (
                <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>Загрузка…</div>
              )}
              {receipts[m.id] && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {receipts[m.id].map((r) => (
                    <div key={r.user_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                      <span>{r.name ?? `#${r.user_id}`}</span>
                      <span style={{ color: r.acked_at ? '#16a34a' : 'var(--text-dim)' }}>
                        {r.acked_at ? formatDateTime(r.acked_at) : 'не прочитано'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
