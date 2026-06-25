import { useCallback, useEffect, useState } from 'react'
import { listOrders } from '../../api/endpoints'
import type { Order } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { MultiButtonGroup } from '../../ui/MultiButtonGroup'
import { TextInput } from '../../ui/Field'
import { StatusChip } from '../../ui/StatusChip'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import { formatDateTime } from '../../lib/format'
import { OrderCreate } from './OrderCreate'
import { OrderDetail } from './OrderDetail'
import { OrdersTable } from './OrdersTable'
import styles from './OrdersPage.module.css'

type View = 'list' | 'table'

const PAGE_SIZE = 100

export function OrdersPage() {
  const ref = useReference()
  const orderStatuses = ref.statusesByType('orders')
  const orderMethods = ref.order_methods

  const [creating, setCreating] = useState(false)
  const [editOrder, setEditOrder] = useState<Order | null>(null)
  const [viewingId, setViewingId] = useState<number | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [view, setView] = useState<View>('list')
  const [statusFilter, setStatusFilter] = useState<number[]>([])
  const [methodFilter, setMethodFilter] = useState<number[]>([])
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    setPage(1)
  }, [statusFilter, methodFilter, debouncedSearch])

  const reload = useCallback(() => {
    setLoading(true)
    listOrders({ statusIds: statusFilter, methodIds: methodFilter, search: debouncedSearch, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setOrders(res.items)
        setTotal(res.pagination?.total ?? res.items.length)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [statusFilter, methodFilter, debouncedSearch, page])

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
          <div className={styles.viewToggle}>
            <ButtonGroup<View>
              columns={2}
              size="sm"
              value={view}
              onChange={(v) => v && setView(v)}
              options={[
                { value: 'list', label: 'Список' },
                { value: 'table', label: 'Таблица' },
              ]}
            />
          </div>
        </div>
        <Button variant="primary" onClick={() => setCreating(true)}>
          + Создать заказ
        </Button>
      </header>

      <div className={styles.filters}>
        <div className={styles.filtersTop}>
          <TextInput
            placeholder="Поиск по клиенту или информации…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className={styles.pager}>
            <Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>
              ←
            </Button>
            <span className={styles.pageInfo}>
              Стр.{' '}
              <input
                className={styles.pageInput}
                type="number"
                min={1}
                max={totalPages}
                value={page}
                onChange={(e) => {
                  const n = Number(e.target.value)
                  if (n >= 1 && n <= totalPages) setPage(n)
                }}
              />{' '}
              из {totalPages}
            </span>
            <Button variant="secondary" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>
              →
            </Button>
          </div>
        </div>
        {orderStatuses.length > 0 && (
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Статус</span>
            <MultiButtonGroup
              size="sm"
              value={statusFilter}
              onChange={setStatusFilter}
              options={orderStatuses.map((s) => ({
                value: s.status_id,
                label: s.status_status,
                dot: s.status_color ?? undefined,
              }))}
            />
          </div>
        )}
        {orderMethods.length > 0 && (
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Способ</span>
            <MultiButtonGroup
              size="sm"
              value={methodFilter}
              onChange={setMethodFilter}
              options={orderMethods.map((m) => ({
                value: m.order_method_id,
                label: m.order_method_name,
              }))}
            />
          </div>
        )}
      </div>

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
      {loading ? (
        <div className="dim">Загрузка…</div>
      ) : orders.length === 0 ? (
        <div className={styles.empty}>Заказов не найдено</div>
      ) : view === 'table' ? (
        <OrdersTable
          orders={orders}
          onOrderPatched={(o) =>
            setOrders((prev) => prev.map((x) => (x.order_id === o.order_id ? o : x)))
          }
        />
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
