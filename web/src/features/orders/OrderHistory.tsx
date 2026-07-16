import { useEffect, useState } from 'react'
import { getOrderHistory, type OrderHistoryEntry } from '../../api/endpoints'
import { useRealtime } from '../../data/RealtimeContext'
import styles from './OrderHistory.module.css'

function timeLabel(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Эмодзи-маркер под тип действия (иконотеки в проекте нет — используем глифы).
const KIND_ICON: Record<string, string> = {
  create: '🆕',
  order_status: '🔄',
  item_status: '📦',
  edit: '✏️',
  split: '✂️',
  comment: '💬',
  delete: '🗑️',
  cdek: '🚚',
}

export function OrderHistory({ orderId }: { orderId: number }) {
  const { revision } = useRealtime()
  const [entries, setEntries] = useState<OrderHistoryEntry[]>([])
  const [loaded, setLoaded] = useState(false)

  // Загрузка при открытии и на каждое realtime-событие (статусы/правки меняются в ленте).
  useEffect(() => {
    let alive = true
    getOrderHistory(orderId)
      .then(({ items }) => {
        if (alive) {
          setEntries(items)
          setLoaded(true)
        }
      })
      .catch(() => {
        if (alive) setLoaded(true)
      })
    return () => {
      alive = false
    }
  }, [orderId, revision])

  return (
    <div className={styles.history}>
      <div className={styles.list}>
        {entries.length === 0 ? (
          <div className={styles.empty}>{loaded ? 'История пуста' : 'Загрузка…'}</div>
        ) : (
          // Бэкенд отдаёт события по убыванию даты — новые сверху.
          entries.map((e, i) => (
            <div key={`${e.audit_event_id}-${i}`} className={styles.row}>
              <span className={styles.icon} aria-hidden>
                {KIND_ICON[e.kind] ?? '•'}
              </span>
              <div className={styles.body}>
                <div className={styles.line}>
                  <span className={styles.actor}>{e.actor_name}</span>{' '}
                  <span className={styles.text}>{e.text}</span>
                </div>
                <div className={styles.time}>{timeLabel(e.created_at)}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
