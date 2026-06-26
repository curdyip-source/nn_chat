import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { listOrders } from '../../api/endpoints'
import type { Order } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { Button } from '../../ui/Button'
import { MultiButtonGroup } from '../../ui/MultiButtonGroup'
import { SegmentedControl } from '../../ui/SegmentedControl'
import { TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { StatusChip } from '../../ui/StatusChip'
import { StatusSelect } from '../../ui/StatusSelect'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import { formatDateTime } from '../../lib/format'
import { ItemStatusExtraModal } from './ItemStatusExtraModal'
import { statusExtraMode, type ExtraMode, type ItemExtra } from './itemStatusExtra'
import { OrderSelectionContext, type BulkApplyFn, type BulkRemoveFn, type OrderSelection } from './orderSelection'
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
  const establishments = ref.establishments
  const itemStatusOptions = ref.statusesByType('order_products').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))

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
  const [establishmentFilter, setEstablishmentFilter] = useState<number[]>([])
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  // --- Массовое выделение позиций (чекбоксы в табличном виде) ---
  const [selected, setSelected] = useState<Record<number, string[]>>({})
  const [bulkPending, setBulkPending] = useState<{ statusId: number; mode: ExtraMode } | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const applyFns = useRef<Map<number, BulkApplyFn>>(new Map())
  const removeFns = useRef<Map<number, BulkRemoveFn>>(new Map())
  const selectionCount = useMemo(() => Object.values(selected).reduce((n, arr) => n + arr.length, 0), [selected])

  const registerApply = useCallback((orderId: number, fn: BulkApplyFn) => {
    applyFns.current.set(orderId, fn)
  }, [])
  const unregisterApply = useCallback((orderId: number) => {
    applyFns.current.delete(orderId)
  }, [])
  const registerRemove = useCallback((orderId: number, fn: BulkRemoveFn) => {
    removeFns.current.set(orderId, fn)
  }, [])
  const unregisterRemove = useCallback((orderId: number) => {
    removeFns.current.delete(orderId)
  }, [])
  const selection = useMemo<OrderSelection>(
    () => ({
      isSelected: (orderId, uid) => (selected[orderId] ?? []).includes(uid),
      toggle: (orderId, uid) =>
        setSelected((prev) => {
          const cur = prev[orderId] ?? []
          const nextArr = cur.includes(uid) ? cur.filter((x) => x !== uid) : [...cur, uid]
          const copy = { ...prev }
          if (nextArr.length) copy[orderId] = nextArr
          else delete copy[orderId]
          return copy
        }),
      registerApply,
      unregisterApply,
      registerRemove,
      unregisterRemove,
    }),
    [selected, registerApply, unregisterApply, registerRemove, unregisterRemove],
  )

  const applyBulkStatus = (statusId: number, extra: ItemExtra) => {
    for (const [orderId, uids] of Object.entries(selected)) {
      applyFns.current.get(Number(orderId))?.(uids, statusId, extra)
    }
    setSelected({})
  }
  const onBulkStatus = (sid: number) => {
    const mode = statusExtraMode(itemStatusOptions.find((o) => o.id === sid)?.label)
    if (mode) setBulkPending({ statusId: sid, mode })
    else applyBulkStatus(sid, {})
  }
  const applyBulkRemove = () => {
    for (const [orderId, uids] of Object.entries(selected)) {
      removeFns.current.get(Number(orderId))?.(uids)
    }
    setSelected({})
    setConfirmDelete(false)
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    setPage(1)
  }, [statusFilter, methodFilter, establishmentFilter, debouncedSearch])

  // Состав строк меняется (фильтры/страница/режим) — сбрасываем отметки, чтобы uid не зависли.
  useEffect(() => {
    setSelected({})
  }, [view, statusFilter, methodFilter, establishmentFilter, debouncedSearch, page])

  const reload = useCallback(() => {
    setLoading(true)
    listOrders({ statusIds: statusFilter, methodIds: methodFilter, establishmentIds: establishmentFilter, search: debouncedSearch, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setOrders(res.items)
        setTotal(res.pagination?.total ?? res.items.length)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [statusFilter, methodFilter, establishmentFilter, debouncedSearch, page])

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
        <h1 className={styles.title}>Заказы</h1>
        <Button variant="primary" onClick={() => setCreating(true)}>
          + Создать заказ
        </Button>
      </header>

      <div className={styles.filters}>
        <div className={styles.filtersTop}>
          <SegmentedControl<View>
            value={view}
            onChange={setView}
            options={[
              { value: 'list', label: 'Список' },
              { value: 'table', label: 'Таблица' },
            ]}
          />
          <TextInput
            placeholder="Поиск по клиенту или информации…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {view === 'table' && itemStatusOptions.length > 0 && (
            <div className={styles.bulkActions}>
              <span title={selectionCount === 0 ? 'Отметьте позиции галочкой' : `Статус для ${selectionCount} поз.`}>
                <StatusSelect value={null} options={itemStatusOptions} onChange={onBulkStatus} saving={selectionCount === 0} />
              </span>
              <button
                type="button"
                className={styles.bulkDelete}
                disabled={selectionCount === 0}
                onClick={() => setConfirmDelete(true)}
                title={selectionCount === 0 ? 'Отметьте позиции галочкой' : `Удалить ${selectionCount} поз.`}
              >
                Удалить
              </button>
            </div>
          )}
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
          <MultiButtonGroup
            size="xs"
            value={statusFilter}
            onChange={setStatusFilter}
            options={orderStatuses.map((s) => ({
              value: s.status_id,
              label: s.status_status,
              dot: s.status_color ?? undefined,
            }))}
          />
        )}
        {orderMethods.length > 0 && (
          <MultiButtonGroup
            size="xs"
            value={methodFilter}
            onChange={setMethodFilter}
            options={orderMethods.map((m) => ({
              value: m.order_method_id,
              label: m.order_method_name,
            }))}
          />
        )}
        {establishments.length > 0 && (
          <MultiButtonGroup
            size="xs"
            value={establishmentFilter}
            onChange={setEstablishmentFilter}
            options={establishments.map((e) => ({
              value: e.establishment_id,
              label: e.establishment_name,
            }))}
          />
        )}
      </div>

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
      {loading && orders.length === 0 ? (
        <div className="dim">Загрузка…</div>
      ) : orders.length === 0 ? (
        <div className={styles.empty}>Заказов не найдено</div>
      ) : view === 'table' ? (
        <OrderSelectionContext.Provider value={selection}>
          <OrdersTable
            orders={orders}
            onOrderPatched={(o) =>
              setOrders((prev) => prev.map((x) => (x.order_id === o.order_id ? o : x)))
            }
          />
        </OrderSelectionContext.Provider>
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

      {bulkPending && (
        <ItemStatusExtraModal
          mode={bulkPending.mode}
          initial={{}}
          onCancel={() => setBulkPending(null)}
          onConfirm={(extra) => {
            applyBulkStatus(bulkPending.statusId, extra)
            setBulkPending(null)
          }}
        />
      )}

      <Modal
        open={confirmDelete}
        title="Удалить позиции"
        onClose={() => setConfirmDelete(false)}
        width={420}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
              Отмена
            </Button>
            <Button variant="danger" onClick={applyBulkRemove}>
              Удалить
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.5 }}>
          Точно удалить все отмеченные товары ({selectionCount})? Действие необратимо.
        </p>
        <p style={{ margin: '10px 0 0', fontSize: 13, lineHeight: 1.5, color: 'var(--text-muted)' }}>
          Если в заказе всего один товар, он не будет удалён — заказ не может остаться без позиций.
        </p>
      </Modal>
    </div>
  )
}
