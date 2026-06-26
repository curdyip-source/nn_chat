import { useEffect, useRef, useState } from 'react'
import { updateOrder, updateOrderStatus } from '../../api/endpoints'
import type { Order, OrderUpdateItem, Product } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { Checkbox } from '../../ui/Checkbox'
import { StatusSelect } from '../../ui/StatusSelect'
import { formatAmount, formatDateTime } from '../../lib/format'
import { AddItemModal } from './AddItemModal'
import { newUid } from './cart'
import { ItemStatusExtraModal } from './ItemStatusExtraModal'
import { showsMovement, showsSupplier, statusExtraMode, type ExtraMode, type ItemExtra } from './itemStatusExtra'
import { useOrderSelection, type BulkApplyFn, type BulkRemoveFn } from './orderSelection'
import { orderToUpdate } from './orderUpdate'
import styles from './OrdersTable.module.css'

type ItemDraft = {
  uid: string
  productId: number | null
  article: string | null
  name: string
  quantity: number
  price: string
  currencyId: number | null
  statusId: number | null
  supplier: string | null
  sourceEstablishmentId: number | null
  destinationEstablishmentId: number | null
}

function toApiItem(d: ItemDraft): OrderUpdateItem {
  return {
    product_id: d.productId,
    product_article: d.productId ? null : d.article,
    product_name: d.productId ? null : d.name,
    order_item_quantity: d.quantity,
    order_item_price: (Number(d.price) || 0).toFixed(2),
    order_item_status_id: d.statusId,
    order_item_currency_id: d.currencyId,
    order_item_supplier: d.supplier,
    order_item_source_establishment_id: d.sourceEstablishmentId,
    order_item_destination_establishment_id: d.destinationEstablishmentId,
  }
}

export function OrdersTable({
  orders,
  onOrderPatched,
}: {
  orders: Order[]
  onOrderPatched: (order: Order) => void
}) {
  return (
    <div className={styles.table}>
      {orders.map((o) => (
        <OrderRow key={o.order_id} order={o} onOrderPatched={onOrderPatched} />
      ))}
    </div>
  )
}

function OrderRow({ order, onOrderPatched }: { order: Order; onOrderPatched: (o: Order) => void }) {
  const ref = useReference()
  const defaultCurrencyId = ref.defaultCurrency?.currency_id ?? null
  const orderStatusOptions = ref.statusesByType('orders').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))
  const itemStatusOptions = ref.statusesByType('order_products').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))
  const currencySign = (id: number | null) => ref.currencies.find((c) => c.currency_id === id)?.currency_sign ?? ''
  const establishmentName = (id: number | null) => ref.establishments.find((e) => e.establishment_id === id)?.establishment_name ?? '—'

  // Подпись под статусом: для перемещения «Склад → Склад», для заказа поставщику/заказано — поставщик.
  const itemExtraLabel = (d: ItemDraft): string | null => {
    const name = itemStatusOptions.find((o) => o.id === d.statusId)?.label
    if (showsMovement(name) && d.sourceEstablishmentId != null && d.destinationEstablishmentId != null) {
      return `${establishmentName(d.sourceEstablishmentId)} → ${establishmentName(d.destinationEstablishmentId)}`
    }
    if (showsSupplier(name) && d.supplier) return d.supplier
    return null
  }

  const [expanded, setExpanded] = useState(true)
  const [addOpen, setAddOpen] = useState(false)
  const [pendingExtra, setPendingExtra] = useState<{ uid: string; statusId: number; mode: ExtraMode } | null>(null)
  const [customer, setCustomer] = useState(order.order_customer)
  const [info, setInfo] = useState(order.order_info)
  const [error, setError] = useState('')
  const [drafts, setDrafts] = useState<ItemDraft[]>(
    order.items.map((it) => ({
      uid: newUid(),
      productId: it.order_item_product_id ?? null,
      article: it.order_item_article,
      name: it.order_item_name,
      quantity: it.order_item_quantity,
      price: it.order_item_price,
      currencyId: it.order_item_currency_id ?? null,
      statusId: it.order_item_status_id ?? null,
      supplier: it.order_item_supplier ?? null,
      sourceEstablishmentId: it.order_item_source_establishment_id ?? null,
      destinationEstablishmentId: it.order_item_destination_establishment_id ?? null,
    })),
  )
  const timer = useRef<number | null>(null)

  const persist = (overrides: { customer?: string; info?: string; drafts?: ItemDraft[] }) => {
    const body = orderToUpdate(order, {
      customer: (overrides.customer ?? customer).trim() || order.order_customer,
      info: overrides.info ?? info,
      items: (overrides.drafts ?? drafts).map(toApiItem),
    })
    return updateOrder(order.order_id, body)
      .then((r) => {
        onOrderPatched(r.item)
        setError('')
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Не удалось сохранить'))
  }

  const scheduleSave = (next: ItemDraft[]) => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = window.setTimeout(() => void persist({ drafts: next }), 500)
  }

  const patchDraft = (uid: string, patch: Partial<ItemDraft>) => {
    const next = drafts.map((d) => (d.uid === uid ? { ...d, ...patch } : d))
    setDrafts(next)
    scheduleSave(next)
  }
  const defaultItemStatusId = itemStatusOptions.find((o) => o.label === 'Не обработан')?.id ?? null
  const addProduct = (p: Product, price: string, quantity: number) => {
    const next = [
      ...drafts,
      { uid: newUid(), productId: p.product_id, article: p.product_article, name: p.product_name, quantity, price, currencyId: defaultCurrencyId, statusId: defaultItemStatusId, supplier: null, sourceEstablishmentId: null, destinationEstablishmentId: null },
    ]
    setDrafts(next)
    void persist({ drafts: next })
  }

  // Массовое применение статуса к отмеченным позициям (из шапки страницы).
  const selection = useOrderSelection()
  const applyBulkRef = useRef<BulkApplyFn>(() => {})
  applyBulkRef.current = (uids, statusId, extra) => {
    setDrafts((prev) => {
      const next = prev.map((d) =>
        uids.includes(d.uid)
          ? {
              ...d,
              statusId,
              supplier: extra.supplier !== undefined ? extra.supplier : d.supplier,
              sourceEstablishmentId: extra.sourceEstablishmentId !== undefined ? extra.sourceEstablishmentId : d.sourceEstablishmentId,
              destinationEstablishmentId: extra.destinationEstablishmentId !== undefined ? extra.destinationEstablishmentId : d.destinationEstablishmentId,
            }
          : d,
      )
      void persist({ drafts: next })
      return next
    })
  }
  useEffect(() => {
    const fn: BulkApplyFn = (uids, s, e) => applyBulkRef.current(uids, s, e)
    selection.registerApply(order.order_id, fn)
    return () => selection.unregisterApply(order.order_id)
  }, [order.order_id, selection.registerApply, selection.unregisterApply])

  const removeBulkRef = useRef<BulkRemoveFn>(() => {})
  removeBulkRef.current = (uids) => {
    setDrafts((prev) => {
      const next = prev.filter((d) => !uids.includes(d.uid))
      // Заказ не может остаться без позиций — если выделены все, эту строку пропускаем.
      if (next.length === 0) return prev
      void persist({ drafts: next })
      return next
    })
  }
  useEffect(() => {
    const fn: BulkRemoveFn = (uids) => removeBulkRef.current(uids)
    selection.registerRemove(order.order_id, fn)
    return () => selection.unregisterRemove(order.order_id)
  }, [order.order_id, selection.registerRemove, selection.unregisterRemove])

  const onItemStatus = (d: ItemDraft, sid: number) => {
    const name = itemStatusOptions.find((o) => o.id === sid)?.label
    const mode = statusExtraMode(name)
    if (mode) setPendingExtra({ uid: d.uid, statusId: sid, mode })
    else patchDraft(d.uid, { statusId: sid })
  }
  const removeItem = (uid: string) => {
    if (drafts.length <= 1) {
      setError('Нельзя удалить последнюю позицию заказа')
      return
    }
    const next = drafts.filter((d) => d.uid !== uid)
    setDrafts(next)
    void persist({ drafts: next })
  }

  const changeStatus = (statusId: number) => {
    void updateOrderStatus(order.order_id, statusId)
      .then((r) => onOrderPatched(r.item))
      .catch((e) => setError(e instanceof Error ? e.message : 'Не удалось сменить статус'))
  }

  const saveCustomer = () => {
    if (customer.trim() && customer.trim() !== order.order_customer) void persist({ customer: customer.trim() })
  }
  const saveInfo = () => {
    if (info !== order.order_info) void persist({ info })
  }

  const totals = new Map<string, number>()
  for (const d of drafts) {
    const sign = currencySign(d.currencyId) || '—'
    totals.set(sign, (totals.get(sign) ?? 0) + (Number(d.price) || 0) * d.quantity)
  }
  const totalText = [...totals.entries()].map(([s, v]) => `${formatAmount(v)}${s}`).join(' · ')

  const metaText = [order.order_establishment_name, order.order_method_name, order.order_sub_method, order.order_contact_method]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className={styles.orderBlock}>
      <div className={styles.row}>
        <button className={styles.expandBtn} onClick={() => setExpanded((v) => !v)}>
          {expanded ? '▾' : '▸'}
        </button>
        <span className={styles.no}>{order.order_id}</span>
        <input className={styles.cellInput} value={customer} onChange={(e) => setCustomer(e.target.value)} onBlur={saveCustomer} />
        <span className={styles.dim} title={metaText}>{metaText}</span>
        <StatusSelect size="sm" value={order.order_status_id} options={orderStatusOptions} onChange={changeStatus} />
        <span className={styles.right}>{drafts.length}</span>
        <span className={styles.dim}>{formatDateTime(order.order_created_at)}</span>
        <span className={styles.orderTotal}>
          <span className={styles.totalLabel}>Итого</span>
          {totalText || '—'}
        </span>
      </div>

      {expanded && (
        <div className={styles.expand}>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Информация</span>
            <input
              className={styles.infoInput}
              placeholder="Заметка по заказу…"
              value={info}
              onChange={(e) => setInfo(e.target.value)}
              onBlur={saveInfo}
            />
            <Button
              variant="secondary"
              style={{ height: 38, minHeight: 38, padding: '0 16px', flex: '0 0 auto' }}
              onClick={() => setAddOpen(true)}
            >
              + Товар
            </Button>
          </div>

          {drafts.map((d) => (
            <div key={d.uid} className={styles.itemRow}>
              <Checkbox
                checked={selection.isSelected(order.order_id, d.uid)}
                onChange={() => selection.toggle(order.order_id, d.uid)}
                title="Отметить для массового статуса"
              />
              <span className={styles.itemName} title={d.name}>
                {d.name}
              </span>
              <input
                className={styles.qty}
                type="number"
                min={1}
                value={d.quantity}
                onChange={(e) => patchDraft(d.uid, { quantity: Math.max(1, Number(e.target.value) || 1) })}
              />
              <input
                className={styles.price}
                inputMode="decimal"
                value={d.price}
                onChange={(e) => patchDraft(d.uid, { price: e.target.value.replace(',', '.') })}
              />
              <select className={styles.curr} value={d.currencyId ?? ''} onChange={(e) => patchDraft(d.uid, { currencyId: Number(e.target.value) })}>
                {ref.currencies.map((c) => (
                  <option key={c.currency_id} value={c.currency_id}>
                    {c.currency_sign || c.currency_name}
                  </option>
                ))}
              </select>
              <span className={styles.itemStatus}>
                {itemStatusOptions.length > 0 && (
                  <StatusSelect size="sm" value={d.statusId} options={itemStatusOptions} onChange={(sid) => onItemStatus(d, sid)} />
                )}
                {itemExtraLabel(d) && (
                  <span className={styles.itemStatusExtra} title={itemExtraLabel(d) ?? ''}>
                    {itemExtraLabel(d)}
                  </span>
                )}
              </span>
              <span className={styles.itemSum}>
                {formatAmount((Number(d.price) || 0) * d.quantity)}
                {currencySign(d.currencyId)}
              </span>
              <button className={styles.delBtn} onClick={() => removeItem(d.uid)} title="Убрать позицию">
                ✕
              </button>
            </div>
          ))}

          {error && <div className={styles.rowError}>{error}</div>}
        </div>
      )}

      <AddItemModal open={addOpen} onClose={() => setAddOpen(false)} onAdd={addProduct} />

      {pendingExtra && (() => {
        const d = drafts.find((x) => x.uid === pendingExtra.uid)
        if (!d) return null
        const initial: ItemExtra = { supplier: d.supplier, sourceEstablishmentId: d.sourceEstablishmentId, destinationEstablishmentId: d.destinationEstablishmentId }
        return (
          <ItemStatusExtraModal
            mode={pendingExtra.mode}
            initial={initial}
            onCancel={() => setPendingExtra(null)}
            onConfirm={(extra) => {
              patchDraft(pendingExtra.uid, { statusId: pendingExtra.statusId, ...extra })
              setPendingExtra(null)
            }}
          />
        )
      })()}
    </div>
  )
}
