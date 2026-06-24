import { useCallback, useEffect, useState } from 'react'
import { Button } from '../../ui/Button'
import { StatusChip } from '../../ui/StatusChip'
import { formatDateTime } from '../../lib/format'
import { DocumentComposer } from './DocumentComposer'
import { DocumentDetail } from './DocumentDetail'
import type { DocKind, DocView } from './docKind'
import styles from './documents.module.css'

export function DocumentsPage({ kind }: { kind: DocKind }) {
  const [creating, setCreating] = useState(false)
  const [viewingId, setViewingId] = useState<number | null>(null)
  const [docs, setDocs] = useState<DocView[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    kind
      .list(1, 50)
      .then((res) => {
        setDocs(res.items)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [kind])

  useEffect(() => {
    if (!creating && viewingId == null) reload()
  }, [creating, viewingId, reload])

  if (creating) {
    return <DocumentComposer kind={kind} onCancel={() => setCreating(false)} onCreated={() => setCreating(false)} />
  }
  if (viewingId != null) {
    return <DocumentDetail kind={kind} id={viewingId} onBack={() => setViewingId(null)} />
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.pageTitle}>{kind.title}</h1>
          <p className="muted">Список и создание</p>
        </div>
        <Button variant="primary" onClick={() => setCreating(true)}>
          + Создать
        </Button>
      </header>

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
        {loading ? (
          <div className="dim">Загрузка…</div>
        ) : docs.length === 0 ? (
          <div className={styles.empty}>Пока пусто</div>
        ) : (
          <div className={styles.list}>
            {docs.map((d) => (
              <button key={d.id} className={styles.docCard} onClick={() => setViewingId(d.id)}>
                <div className={styles.docTop}>
                  <span className={styles.docNo}>№{d.id}</span>
                  <span className={styles.docSupplier}>{d.supplier || '—'}</span>
                  {d.status && <StatusChip label={d.status} color={d.statusColor} />}
                </div>
                <div className={styles.docMeta}>
                  {[d.establishmentName, d.items.length ? `${d.items.length} поз.` : null, formatDateTime(d.createdAt)]
                    .filter(Boolean)
                    .join(' · ')}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
