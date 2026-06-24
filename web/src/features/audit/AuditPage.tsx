import { useCallback, useEffect, useState } from 'react'
import { listAuditEvents } from '../../api/endpoints'
import type { AuditEvent } from '../../api/types'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { formatDateTime } from '../../lib/format'
import { AUDIT_QUICK_FILTERS, describeAuditEvent } from './describe'
import styles from './AuditPage.module.css'

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [entityType, setEntityType] = useState<string | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    listAuditEvents({ entityType: entityType ?? undefined })
      .then((res) => {
        setEvents(res.items)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [entityType])

  useEffect(reload, [reload])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Аудит</h1>
        <p className="muted">Журнал действий пользователей</p>
      </header>

      <div className={styles.filters}>
        <ButtonGroup
          size="sm"
          value={entityType ?? '__all'}
          onChange={(v) => setEntityType(v === '__all' ? null : (v as string))}
          options={AUDIT_QUICK_FILTERS.map((f) => ({
            value: f.entityType ?? '__all',
            label: f.label,
          }))}
        />
      </div>

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
      {loading ? (
        <div className="dim">Загрузка…</div>
      ) : events.length === 0 ? (
        <div className={styles.empty}>Событий не найдено</div>
      ) : (
        <div className={styles.list}>
          {events.map((ev) => {
            const v = describeAuditEvent(ev)
            return (
              <div key={ev.audit_event_id} className={styles.row}>
                <span className={styles.icon}>{v.icon}</span>
                <div className={styles.body}>
                  <div className={styles.line}>
                    <span className={styles.actor}>
                      {ev.actor_user_login ? `@${ev.actor_user_login}` : 'Система'}
                    </span>
                    <span className={[styles.action, v.isError ? styles.actionError : ''].join(' ')}>
                      {v.title.toLowerCase()}
                    </span>
                    {v.target && <span className={styles.target}>{v.target}</span>}
                  </div>
                  <div className={styles.time}>{formatDateTime(ev.created_at)}</div>
                </div>
              </div>
            )
          })}
        </div>
      )}
      </div>
    </div>
  )
}
