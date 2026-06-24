import { useCallback, useEffect, useState } from 'react'
import { getOrder, updateOrder, updateOrderStatus } from '../../api/endpoints'
import type { Order, OrderUpdate } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { StatusSelect } from '../../ui/StatusSelect'
import { formatAmount, formatDateTime } from '../../lib/format'
import { ItemStatusExtraModal } from './ItemStatusExtraModal'
import { statusExtraMode, type ExtraMode, type ItemExtra } from './itemStatusExtra'
import styles from './OrderDetail.module.css'

function buildUpdatePayload(order: Order): OrderUpdate {
  return {
    order_establishment_id: order.order_establishment_id!,
    order_method_id: order.order_method_id!,
    order_sub_method: order.order_sub_method ?? null,
    order_contact_method: order.order_contact_method ?? null,
    order_customer: order.order_customer,
    order_info: order.order_info,
    order_status_id: order.order_status_id!,
    items: order.items.map((it) => ({
      product_id: it.order_item_product_id ?? null,
      product_article: it.order_item_product_id ? null : it.order_item_article,
      product_name: it.order_item_product_id ? null : it.order_item_name,
      order_item_quantity: it.order_item_quantity,
      order_item_price: it.order_item_price,
      order_item_status_id: it.order_item_status_id ?? null,
      order_item_currency_id: it.order_item_currency_id ?? null,
      order_item_supplier: it.order_item_supplier ?? null,
      order_item_note: it.order_item_note ?? null,
      order_item_source_establishment_id: it.order_item_source_establishment_id ?? null,
      order_item_destination_establishment_id: it.order_item_destination_establishment_id ?? null,
    })),
  }
}

export function OrderDetail({
  orderId,
  onBack,
  onEdit,
}: {
  orderId: number
  onBack: () => void
  onEdit: (order: Order) => void
}) {
  const ref = useReference()
  const orderStatusOptions = ref.statusesByType('orders').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))
  const itemStatusOptions = ref.statusesByType('order_products').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))
  const currencySign = (id: number | null | undefined) =>
    ref.currencies.find((c) => c.currency_id === id)?.currency_sign ?? ''

  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [pendingExtra, setPendingExtra] = useState<{ itemId: number; statusId: number; mode: ExtraMode } | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    getOrder(orderId)
      .then((r) => {
        setOrder(r.item)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [orderId])

  useEffect(load, [load])

  const changeOrderStatus = async (statusId: number) => {
    if (!order) return
    setSaving(true)
    setError(null)
    try {
      const { item } = await updateOrderStatus(order.order_id, statusId)
      setOrder(item)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось изменить статус')
    } finally {
      setSaving(false)
    }
  }

  const applyItemStatus = async (itemId: number, statusId: number, extra?: ItemExtra) => {
    if (!order) return
    setSaving(true)
    setError(null)
    const payload = buildUpdatePayload(order)
    const idx = order.items.findIndex((it) => it.order_item_id === itemId)
    if (idx >= 0) {
      payload.items[idx].order_item_status_id = statusId
      if (extra?.supplier !== undefined) payload.items[idx].order_item_supplier = extra.supplier
      if (extra?.sourceEstablishmentId !== undefined) payload.items[idx].order_item_source_establishment_id = extra.sourceEstablishmentId
      if (extra?.destinationEstablishmentId !== undefined) payload.items[idx].order_item_destination_establishment_id = extra.destinationEstablishmentId
    }
    try {
      const { item } = await updateOrder(order.order_id, payload)
      setOrder(item)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось изменить статус позиции')
    } finally {
      setSaving(false)
    }
  }

  const changeItemStatus = (itemId: number, statusId: number) => {
    const name = itemStatusOptions.find((o) => o.id === statusId)?.label
    const mode = statusExtraMode(name)
    if (mode) setPendingExtra({ itemId, statusId, mode })
    else void applyItemStatus(itemId, statusId)
  }

  const totals = new Map<string, number>()
  for (const it of order?.items ?? []) {
    const sign = currencySign(it.order_item_currency_id) || '—'
    totals.set(sign, (totals.get(sign) ?? 0) + (Number(it.order_item_price) || 0) * it.order_item_quantity)
  }

  return (
    <div className={styles.wrap}>
      <header className={styles.header}>
        <button className={styles.back} onClick={onBack}>
          ← К списку
        </button>
        {order && <h1 className={styles.title}>Заказ №{order.order_id}</h1>}
        {saving && <span className="dim">Сохранение…</span>}
        {order && (
          <Button variant="secondary" style={{ marginLeft: 'auto' }} onClick={() => onEdit(order)}>
            ✏️ Редактировать
          </Button>
        )}
      </header>

      <div className={styles.scroll}>
      {error && <div className={styles.error}>{error}</div>}
      {loading ? (
        <div className="dim">Загрузка…</div>
      ) : !order ? null : (
        <>
          <section className={styles.card}>
            <div className={styles.customerRow}>
              <div>
                <div className={styles.customer}>{order.order_customer}</div>
                <div className={styles.created}>{formatDateTime(order.order_created_at)}</div>
              </div>
              <StatusSelect
                value={order.order_status_id}
                options={orderStatusOptions}
                onChange={changeOrderStatus}
                saving={saving}
              />
            </div>

            {order.order_info && <p className={styles.info}>{order.order_info}</p>}

            <dl className={styles.meta}>
              <Meta label="Склад" value={order.order_establishment_name} />
              <Meta label="Способ" value={order.order_method_name} />
              <Meta label="Подспособ" value={order.order_sub_method} />
              <Meta label="Связь" value={order.order_contact_method} />
            </dl>
          </section>

          <section>
            <div className={styles.sectionTitle}>Товары · {order.items.length}</div>
            <div className={styles.items}>
              {order.items.map((it) => (
                <div key={it.order_item_id} className={styles.item}>
                  <div className={styles.itemMain}>
                    <div className={styles.itemName}>
                      {it.order_item_name}
                      {it.order_item_article && <span className="dim"> · {it.order_item_article}</span>}
                    </div>
                    <div className={styles.itemMeta}>
                      {it.order_item_quantity} × {formatAmount(Number(it.order_item_price) || 0)}
                      {currencySign(it.order_item_currency_id)}
                      {it.order_item_supplier ? ` · ${it.order_item_supplier}` : ''}
                    </div>
                  </div>
                  <div className={styles.itemRight}>
                    <div className={styles.itemSum}>
                      {formatAmount((Number(it.order_item_price) || 0) * it.order_item_quantity)}
                      {currencySign(it.order_item_currency_id)}
                    </div>
                    {itemStatusOptions.length > 0 && (
                      <StatusSelect
                        size="sm"
                        value={it.order_item_status_id}
                        options={itemStatusOptions}
                        onChange={(sid) => changeItemStatus(it.order_item_id, sid)}
                        saving={saving}
                      />
                    )}
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

      {pendingExtra && order && (() => {
        const it = order.items.find((x) => x.order_item_id === pendingExtra.itemId)
        const initial: ItemExtra = {
          supplier: it?.order_item_supplier ?? null,
          sourceEstablishmentId: it?.order_item_source_establishment_id ?? null,
          destinationEstablishmentId: it?.order_item_destination_establishment_id ?? null,
        }
        return (
          <ItemStatusExtraModal
            mode={pendingExtra.mode}
            initial={initial}
            onCancel={() => setPendingExtra(null)}
            onConfirm={(extra) => {
              const { itemId, statusId } = pendingExtra
              setPendingExtra(null)
              void applyItemStatus(itemId, statusId, extra)
            }}
          />
        )
      })()}
    </div>
  )
}

function Meta({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className={styles.metaItem}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}
