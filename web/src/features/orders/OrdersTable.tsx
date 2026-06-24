import { useRef, useState } from 'react'
import { updateOrder, updateOrderStatus } from '../../api/endpoints'
import type { Order, OrderUpdateItem, Product } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { StatusSelect } from '../../ui/StatusSelect'
import { formatAmount, formatDateTime } from '../../lib/format'
import { AddItemModal } from './AddItemModal'
import { newUid } from './cart'
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

  const [expanded, setExpanded] = useState(true)
  const [addOpen, setAddOpen] = useState(false)
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
  const addProduct = (p: Product, price: string, quantity: number) => {
    const next = [
      ...drafts,
      { uid: newUid(), productId: p.product_id, article: p.product_article, name: p.product_name, quantity, price, currencyId: defaultCurrencyId, statusId: null },
    ]
    setDrafts(next)
    void persist({ drafts: next })
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

  return (
    <div className={styles.orderBlock}>
      <div className={styles.row}>
        <button className={styles.expandBtn} onClick={() => setExpanded((v) => !v)}>
          {expanded ? '▾' : '▸'}
        </button>
        <span className={styles.no}>{order.order_id}</span>
        <input className={styles.cellInput} value={customer} onChange={(e) => setCustomer(e.target.value)} onBlur={saveCustomer} />
        <span className={styles.dim}>{order.order_establishment_name}</span>
        <StatusSelect size="sm" value={order.order_status_id} options={orderStatusOptions} onChange={changeStatus} />
        <span className={styles.right}>{drafts.length}</span>
        <span className={styles.dim}>{formatDateTime(order.order_created_at)}</span>
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
          </div>

          {drafts.map((d) => (
            <div key={d.uid} className={styles.itemRow}>
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
              {itemStatusOptions.length > 0 && (
                <StatusSelect size="sm" value={d.statusId} options={itemStatusOptions} onChange={(sid) => patchDraft(d.uid, { statusId: sid })} />
              )}
              <span className={styles.itemSum}>
                {formatAmount((Number(d.price) || 0) * d.quantity)}
                {currencySign(d.currencyId)}
              </span>
              <button className={styles.delBtn} onClick={() => removeItem(d.uid)} title="Убрать позицию">
                ✕
              </button>
            </div>
          ))}

          <div className={styles.addRow}>
            <Button variant="secondary" onClick={() => setAddOpen(true)}>
              + Товар
            </Button>
          </div>

          {error && <div className={styles.rowError}>{error}</div>}
        </div>
      )}

      <AddItemModal open={addOpen} onClose={() => setAddOpen(false)} onAdd={addProduct} />
    </div>
  )
}
