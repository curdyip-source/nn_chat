import { useCallback, useEffect, useState } from 'react'
import { listOrders } from '../../api/endpoints'
import type { Order } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { TextInput } from '../../ui/Field'
import { StatusChip } from '../../ui/StatusChip'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import { formatDateTime } from '../../lib/format'
import { OrderCreate } from './OrderCreate'
import { OrderDetail } from './OrderDetail'
import { OrdersTable } from './OrdersTable'
import styles from './OrdersPage.module.css'

type View = 'list' | 'table'

export function OrdersPage() {
  const ref = useReference()
  const orderStatuses = ref.statusesByType('orders')

  const [creating, setCreating] = useState(false)
  const [editOrder, setEditOrder] = useState<Order | null>(null)
  const [viewingId, setViewingId] = useState<number | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [view, setView] = useState<View>('list')
  const [statusFilter, setStatusFilter] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const reload = useCallback(() => {
    setLoading(true)
    listOrders({ statusId: statusFilter, search: debouncedSearch })
      .then((res) => {
        setOrders(res.items)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [statusFilter, debouncedSearch])

  useEffect(() => {
    if (!creating && viewingId == null && editOrder == null) reload()
  }, [creating, viewingId, editOrder, reload])

  if (creating || editOrder) {
    return (
      <OrderCreate
        editOrder={editOrder}
        onCancel={() => {
          setCreating(false)
          setEditOrder(null)
        }}
        onCreated={() => {
          setCreating(false)
          setEditOrder(null)
        }}
      />
    )
  }

  if (viewingId != null) {
    return (
      <OrderDetail
        orderId={viewingId}
        onBack={() => setViewingId(null)}
        onEdit={(order) => {
          setViewingId(null)
          setEditOrder(order)
        }}
      />
    )
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Заказы</h1>
          <p className="muted">Последние заказы и создание нового</p>
        </div>
        <div className={styles.headerActions}>
          <ButtonGroup<View>
            size="sm"
            value={view}
            onChange={(v) => v && setView(v)}
            options={[
              { value: 'list', label: 'Список' },
              { value: 'table', label: 'Таблица' },
            ]}
          />
          <Button variant="primary" onClick={() => setCreating(true)}>
            + Создать заказ
          </Button>
        </div>
      </header>

      <div className={styles.filters}>
        <TextInput
          placeholder="Поиск по клиенту или информации…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {orderStatuses.length > 0 && (
          <ButtonGroup
            deselectable
            size="sm"
            value={statusFilter}
            onChange={setStatusFilter}
            options={orderStatuses.map((s) => ({
              value: s.status_id,
              label: s.status_status,
              dot: s.status_color ?? undefined,
            }))}
          />
        )}
      </div>

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
      {loading ? (
        <div className="dim">Загрузка…</div>
      ) : orders.length === 0 ? (
        <div className={styles.empty}>Заказов не найдено</div>
      ) : view === 'table' ? (
        <OrdersTable orders={orders} onChanged={reload} />
      ) : (
        <div className={styles.list}>
          {orders.map((o) => (
            <button key={o.order_id} className={styles.card} onClick={() => setViewingId(o.order_id)}>
              <div className={styles.cardTop}>
                <span className={styles.orderNo}>№{o.order_id}</span>
                <span className={styles.customer}>{o.order_customer}</span>
                {o.order_status && <StatusChip label={o.order_status} color={o.order_status_color} />}
              </div>
              <div className={styles.cardMeta}>
                {[
                  o.order_establishment_name,
                  o.order_method_name,
                  o.items?.length ? `${o.items.length} поз.` : null,
                  formatDateTime(o.order_created_at),
                ]
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
