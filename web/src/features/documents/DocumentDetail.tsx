import { useCallback, useEffect, useState } from 'react'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { StatusSelect } from '../../ui/StatusSelect'
import { formatAmount, formatDateTime } from '../../lib/format'
import type { DocKind, DocView } from './docKind'
import styles from './documents.module.css'

export function DocumentDetail({
  kind,
  id,
  onBack,
  onEdit,
}: {
  kind: DocKind
  id: number
  onBack: () => void
  onEdit: (doc: DocView) => void
}) {
  const ref = useReference()
  const statusOptions = ref
    .statusesByType(kind.statusType)
    .map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))
  const currencySign = (cid: number | null) =>
    ref.currencies.find((c) => c.currency_id === cid)?.currency_sign ?? ''

  const [doc, setDoc] = useState<DocView | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    kind
      .get(id)
      .then((d) => {
        setDoc(d)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [kind, id])

  useEffect(load, [load])

  const changeStatus = async (statusId: number) => {
    if (!doc) return
    setSaving(true)
    setError(null)
    try {
      setDoc(await kind.updateStatus(doc.id, statusId))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось изменить статус')
    } finally {
      setSaving(false)
    }
  }

  const totals = new Map<string, number>()
  for (const it of doc?.items ?? []) {
    const sign = currencySign(it.currencyId) || '—'
    totals.set(sign, (totals.get(sign) ?? 0) + (Number(it.cost) || 0) * it.quantity)
  }

  return (
    <div className={styles.wrap}>
      <header className={styles.cHeader}>
        <button className={styles.back} onClick={onBack}>
          ← К списку
        </button>
        {doc && <h1 className={styles.title}>{kind.singular} №{doc.id}</h1>}
        {saving && <span className="dim">Сохранение…</span>}
        {doc && (
          <Button variant="secondary" style={{ marginLeft: 'auto' }} onClick={() => onEdit(doc)}>
            ✏️ Редактировать
          </Button>
        )}
      </header>

      <div className={styles.scroll}>
        {error && <div className={styles.error}>{error}</div>}
        {loading ? (
          <div className="dim">Загрузка…</div>
        ) : !doc ? null : (
          <>
            <section className={styles.card}>
              <div className={styles.customerRow}>
                <div>
                  <div className={styles.customer}>{doc.supplier || '—'}</div>
                  <div className={styles.created}>{formatDateTime(doc.createdAt)}</div>
                </div>
                <StatusSelect value={doc.statusId} options={statusOptions} onChange={changeStatus} saving={saving} />
              </div>
              <dl className={styles.meta}>
                <div className={styles.metaItem}>
                  <dt>{kind.supplierLabel}</dt>
                  <dd>{doc.supplier || '—'}</dd>
                </div>
                <div className={styles.metaItem}>
                  <dt>Склад</dt>
                  <dd>{doc.establishmentName || '—'}</dd>
                </div>
              </dl>
            </section>

            <section>
              <div className={styles.sectionTitle}>Товары · {doc.items.length}</div>
              <div className={styles.items}>
                {doc.items.map((it) => (
                  <div key={it.id} className={styles.item}>
                    <div className={styles.itemMain}>
                      <div className={styles.itemName}>
                        {it.name}
                        {it.article && <span className="dim"> · {it.article}</span>}
                      </div>
                      <div className={styles.itemMeta}>
                        {it.quantity} × {formatAmount(Number(it.cost) || 0)}
                        {currencySign(it.currencyId)}
                      </div>
                    </div>
                    <div className={styles.itemSum}>
                      {formatAmount((Number(it.cost) || 0) * it.quantity)}
                      {currencySign(it.currencyId)}
                    </div>
                  </div>
                ))}
              </div>
              <div className={styles.totals}>
                {[...totals.entries()].map(([sign, sum]) => (
                  <span key={sign} className={styles.total}>
                    Итого: {formatAmount(sum)}
                    {sign}
                  </span>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}
