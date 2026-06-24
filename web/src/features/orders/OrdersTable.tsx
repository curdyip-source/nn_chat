import { useState } from 'react'
import { updateOrder, updateOrderStatus } from '../../api/endpoints'
import type { Order } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { StatusSelect } from '../../ui/StatusSelect'
import { formatAmount, formatDateTime } from '../../lib/format'
import { orderToUpdate } from './orderUpdate'
import styles from './OrdersTable.module.css'

type ItemDraft = {
  productId: number | null
  article: string | null
  name: string
  quantity: number
  price: string
  currencyId: number | null
  statusId: number | null
}

export function OrdersTable({ orders, onChanged }: { orders: Order[]; onChanged: () => void }) {
  return (
    <div className={styles.table}>
      <div className={[styles.row, styles.head].join(' ')}>
        <span />
        <span>№</span>
        <span>Клиент</span>
        <span>Склад</span>
        <span>Статус</span>
        <span className={styles.right}>Поз.</span>
        <span>Дата</span>
      </div>
      {orders.map((o) => (
        <OrderRow key={o.order_id} order={o} onChanged={onChanged} />
      ))}
    </div>
  )
}

function OrderRow({ order, onChanged }: { order: Order; onChanged: () => void }) {
  const ref = useReference()
  const orderStatusOptions = ref.statusesByType('orders').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))
  const itemStatusOptions = ref.statusesByType('order_products').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))
  const currencySign = (id: number | null) => ref.currencies.find((c) => c.currency_id === id)?.currency_sign ?? ''

  const [expanded, setExpanded] = useState(false)
  const [customer, setCustomer] = useState(order.order_customer)
  const [saving, setSaving] = useState(false)
  const [drafts, setDrafts] = useState<ItemDraft[]>([])

  const openExpand = () => {
    setDrafts(
      order.items.map((it) => ({
        productId: it.order_item_product_id ?? null,
        article: it.order_item_article,
        name: it.order_item_name,
        quantity: it.order_item_quantity,
        price: it.order_item_price,
        currencyId: it.order_item_currency_id ?? null,
        statusId: it.order_item_status_id ?? null,
      })),
    )
    setExpanded(true)
  }

  const saveCustomer = async () => {
    if (customer.trim() === order.order_customer || !customer.trim()) return
    setSaving(true)
    try {
      await updateOrder(order.order_id, orderToUpdate(order, { customer: customer.trim() }))
      onChanged()
    } finally {
      setSaving(false)
    }
  }

  const changeStatus = async (statusId: number) => {
    setSaving(true)
    try {
      await updateOrderStatus(order.order_id, statusId)
      onChanged()
    } finally {
      setSaving(false)
    }
  }

  const patchDraft = (idx: number, patch: Partial<ItemDraft>) =>
    setDrafts((prev) => prev.map((d, i) => (i === idx ? { ...d, ...patch } : d)))

  const saveItems = async () => {
    setSaving(true)
    try {
      await updateOrder(
        order.order_id,
        orderToUpdate(order, {
          items: drafts.map((d) => ({
            product_id: d.productId,
            product_article: d.productId ? null : d.article,
            product_name: d.productId ? null : d.name,
            order_item_quantity: d.quantity,
            order_item_price: (Number(d.price) || 0).toFixed(2),
            order_item_status_id: d.statusId,
            order_item_currency_id: d.currencyId,
          })),
        }),
      )
      setExpanded(false)
      onChanged()
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className={styles.row}>
        <button className={styles.expandBtn} onClick={() => (expanded ? setExpanded(false) : openExpand())}>
          {expanded ? '▾' : '▸'}
        </button>
        <span className={styles.no}>{order.order_id}</span>
        <input
          className={styles.cellInput}
          value={customer}
          onChange={(e) => setCustomer(e.target.value)}
          onBlur={saveCustomer}
        />
        <span className={styles.dim}>{order.order_establishment_name}</span>
        <StatusSelect size="sm" value={order.order_status_id} options={orderStatusOptions} onChange={changeStatus} saving={saving} />
        <span className={styles.right}>{order.items.length}</span>
        <span className={styles.dim}>{formatDateTime(order.order_created_at)}</span>
      </div>

      {expanded && (
        <div className={styles.expand}>
          {drafts.map((d, idx) => (
            <div key={idx} className={styles.itemRow}>
              <span className={styles.itemName} title={d.name}>
                {d.name}
              </span>
              <input
                className={styles.qty}
                type="number"
                min={1}
                value={d.quantity}
                onChange={(e) => patchDraft(idx, { quantity: Math.max(1, Number(e.target.value) || 1) })}
              />
              <input
                className={styles.price}
                inputMode="decimal"
                value={d.price}
                onChange={(e) => patchDraft(idx, { price: e.target.value.replace(',', '.') })}
              />
              <select
                className={styles.curr}
                value={d.currencyId ?? ''}
                onChange={(e) => patchDraft(idx, { currencyId: Number(e.target.value) })}
              >
                {ref.currencies.map((c) => (
                  <option key={c.currency_id} value={c.currency_id}>
                    {c.currency_sign || c.currency_name}
                  </option>
                ))}
              </select>
              {itemStatusOptions.length > 0 && (
                <StatusSelect size="sm" value={d.statusId} options={itemStatusOptions} onChange={(sid) => patchDraft(idx, { statusId: sid })} />
              )}
              <span className={styles.itemSum}>
                {formatAmount((Number(d.price) || 0) * d.quantity)}
                {currencySign(d.currencyId)}
              </span>
            </div>
          ))}
          <div className={styles.expandActions}>
            <Button variant="primary" loading={saving} onClick={saveItems}>
              Сохранить позиции
            </Button>
          </div>
        </div>
      )}
    </>
  )
}
