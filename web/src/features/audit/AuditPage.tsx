import { useCallback, useEffect, useState } from 'react'
import { listAuditEvents } from '../../api/endpoints'
import type { AuditEvent } from '../../api/types'
import { TextInput } from '../../ui/Field'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import { formatDateTime } from '../../lib/format'
import styles from './AuditPage.module.css'

function summarizePayload(payload: Record<string, unknown> | null): string {
  if (!payload) return ''
  try {
    return Object.entries(payload)
      .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
      .join(' · ')
  } catch {
    return ''
  }
}

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [entityType, setEntityType] = useState('')
  const [eventType, setEventType] = useState('')
  const dEntity = useDebouncedValue(entityType.trim(), 300)
  const dEvent = useDebouncedValue(eventType.trim(), 300)

  const reload = useCallback(() => {
    setLoading(true)
    listAuditEvents({ entityType: dEntity || undefined, eventType: dEvent || undefined })
      .then((res) => {
        setEvents(res.items)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [dEntity, dEvent])

  useEffect(reload, [reload])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Аудит</h1>
        <p className="muted">Журнал действий пользователей</p>
      </header>

      <div className={styles.filters}>
        <TextInput
          placeholder="Тип сущности (order, product, user…)"
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
        />
        <TextInput
          placeholder="Тип события (auth.login.succeeded…)"
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
        />
      </div>

      {error && <div className={styles.error}>{error}</div>}
      {loading ? (
        <div className="dim">Загрузка…</div>
      ) : events.length === 0 ? (
        <div className={styles.empty}>Событий не найдено</div>
      ) : (
        <div className={styles.list}>
          {events.map((ev) => (
            <div key={ev.audit_event_id} className={styles.row}>
              <div className={styles.rowTop}>
                <span className={styles.event}>{ev.event_type}</span>
                <span className={styles.time}>{formatDateTime(ev.created_at)}</span>
              </div>
              <div className={styles.rowMeta}>
                {ev.actor_user_login ? `@${ev.actor_user_login}` : 'система'}
                {ev.entity_type ? ` · ${ev.entity_type}${ev.entity_id ? ` #${ev.entity_id}` : ''}` : ''}
              </div>
              {summarizePayload(ev.event_payload) && (
                <div className={styles.payload}>{summarizePayload(ev.event_payload)}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
