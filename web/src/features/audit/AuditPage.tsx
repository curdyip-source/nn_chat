import { useCallback, useEffect, useState } from 'react'
import { listAuditEvents } from '../../api/endpoints'
import type { AuditEvent } from '../../api/types'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { formatDateTime } from '../../lib/format'
import { AUDIT_QUICK_FILTERS, describeAuditEvent, describeCdekWaybill, describeOrderUpdate } from './describe'
import styles from './AuditPage.module.css'

const PAGE_SIZE = 50

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [entityType, setEntityType] = useState<string | null>(null)
  const [total, setTotal] = useState(0)

  const load = useCallback(
    (page: number) => {
      const first = page === 1
      if (first) setLoading(true)
      else setLoadingMore(true)
      listAuditEvents({ entityType: entityType ?? undefined, page, pageSize: PAGE_SIZE })
        .then((res) => {
          // Первая страница (или смена фильтра) — заменяем, иначе дописываем снизу.
          setEvents((prev) => (first ? res.items : [...prev, ...res.items]))
          setTotal(res.pagination?.total ?? res.items.length)
          setError(null)
        })
        .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
        .finally(() => {
          if (first) setLoading(false)
          else setLoadingMore(false)
        })
    },
    [entityType],
  )

  // Смена фильтра → грузим первую страницу заново.
  useEffect(() => {
    load(1)
  }, [load])

  const hasMore = events.length < total
  const loadMore = () => load(Math.floor(events.length / PAGE_SIZE) + 1)

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Аудит</h1>
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
            const details =
              ev.event_type === 'order.update'
                ? describeOrderUpdate(ev.event_payload)
                : ev.event_type === 'cdek.waybill.create'
                  ? describeCdekWaybill(ev.event_payload)
                  : []
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
                  {details.length > 0 && (
                    <ul className={styles.details}>
                      {details.map((d, i) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  )}
                  <div className={styles.time}>{formatDateTime(ev.created_at)}</div>
                </div>
              </div>
            )
          })}
          {hasMore && (
            <div className={styles.loadMore}>
              <Button variant="ghost" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? 'Загрузка…' : 'Загрузить ещё'}
              </Button>
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  )
}
