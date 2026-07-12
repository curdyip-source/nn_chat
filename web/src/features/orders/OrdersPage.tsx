import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { deleteOrder, listOrders, updateOrderStatus, type OrderTotal } from '../../api/endpoints'
import type { Order } from '../../api/types'
import { useReference } from '../../data/ReferenceContext'
import { useRealtime } from '../../data/RealtimeContext'
import { Button } from '../../ui/Button'
import { MultiButtonGroup } from '../../ui/MultiButtonGroup'
import { TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { StatusSelect } from '../../ui/StatusSelect'
import { Switch } from '../../ui/Switch'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import { formatAmount } from '../../lib/format'
import { ItemStatusExtraModal } from './ItemStatusExtraModal'
import { statusExtraMode, type ExtraMode, type ItemExtra } from './itemStatusExtra'
import { OrderSelectionContext, type BulkApplyFn, type BulkCollectFn, type BulkItemInfo, type BulkRemoveFn, type OrderSelection } from './orderSelection'
import { OrderCreate } from './OrderCreate'
import { OrdersTable } from './OrdersTable'
import styles from './OrdersPage.module.css'

const PAGE_SIZE = 100

export function OrdersPage() {
  const ref = useReference()
  const { revision } = useRealtime()
  const orderStatuses = ref.statusesByType('orders')
  const orderMethods = ref.order_methods
  const establishments = ref.establishments
  const itemStatusOptions = ref.statusesByType('order_products').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))
  const orderStatusOptions = ref.statusesByType('orders').map((s) => ({ id: s.status_id, label: s.status_status, color: s.status_color }))

  const [creating, setCreating] = useState(false)
  const [editOrder, setEditOrder] = useState<Order | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [totals, setTotals] = useState<OrderTotal[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [statusFilter, setStatusFilter] = useState<number[]>([])
  const [methodFilter, setMethodFilter] = useState<number[]>([])
  const [establishmentFilter, setEstablishmentFilter] = useState<number[]>([])
  // По умолчанию — весь текущий год: 01.01 … 31.12.
  const defaultDateFrom = useMemo(() => `${new Date().getFullYear()}-01-01`, [])
  const defaultDateTo = useMemo(() => `${new Date().getFullYear()}-12-31`, [])
  const [dateFrom, setDateFrom] = useState(defaultDateFrom)
  const [dateTo, setDateTo] = useState(defaultDateTo)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  // Глобальное сворачивание/разворачивание всех блоков. По умолчанию — развёрнуто.
  const [expandAll, setExpandAll] = useState(true)
  const [expandNonce, setExpandNonce] = useState(0)
  const toggleExpandAll = (value: boolean) => {
    setExpandAll(value)
    setExpandNonce((n) => n + 1)
    // Переключение режима меняет тип чекбоксов (позиции ↔ заказы) — старые отметки
    // становятся неактуальными, сбрасываем оба набора.
    setSelected({})
    setSelectedOrders(new Set())
  }

  const hasActiveFilters =
    statusFilter.length > 0 ||
    methodFilter.length > 0 ||
    establishmentFilter.length > 0 ||
    dateFrom !== defaultDateFrom ||
    dateTo !== defaultDateTo ||
    search !== ''
  const resetAllFilters = () => {
    setStatusFilter([])
    setMethodFilter([])
    setEstablishmentFilter([])
    setDateFrom(defaultDateFrom)
    setDateTo(defaultDateTo)
    setSearch('')
  }

  // --- Массовое выделение позиций (чекбоксы в табличном виде) ---
  const [selected, setSelected] = useState<Record<number, string[]>>({})
  const [bulkPending, setBulkPending] = useState<{ statusId: number; mode: ExtraMode } | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [confirmDeleteOrders, setConfirmDeleteOrders] = useState(false)
  const [deletingOrders, setDeletingOrders] = useState(false)
  const applyFns = useRef<Map<number, BulkApplyFn>>(new Map())
  const removeFns = useRef<Map<number, BulkRemoveFn>>(new Map())
  const collectFns = useRef<Map<number, BulkCollectFn>>(new Map())
  const selectionCount = useMemo(() => Object.values(selected).reduce((n, arr) => n + arr.length, 0), [selected])
  const [actionMenuOpen, setActionMenuOpen] = useState(false)

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
  const registerCollect = useCallback((orderId: number, fn: BulkCollectFn) => {
    collectFns.current.set(orderId, fn)
  }, [])
  const unregisterCollect = useCallback((orderId: number) => {
    collectFns.current.delete(orderId)
  }, [])
  // --- Массовое выделение целых заказов (чекбоксы у свёрнутых строк) ---
  const [selectedOrders, setSelectedOrders] = useState<Set<number>>(new Set())
  const orderSelectionCount = selectedOrders.size

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
      registerCollect,
      unregisterCollect,
      isOrderSelected: (orderId) => selectedOrders.has(orderId),
      toggleOrder: (orderId) =>
        setSelectedOrders((prev) => {
          const next = new Set(prev)
          if (next.has(orderId)) next.delete(orderId)
          else next.add(orderId)
          return next
        }),
    }),
    [selected, selectedOrders, registerApply, unregisterApply, registerRemove, unregisterRemove, registerCollect, unregisterCollect],
  )

  // Собрать данные всех отмеченных позиций (для копирования).
  const collectSelectedItems = () => {
    const out: BulkItemInfo[] = []
    for (const [orderId, uids] of Object.entries(selected)) {
      const fn = collectFns.current.get(Number(orderId))
      if (fn) out.push(...fn(uids))
    }
    return out
  }
  const copyItems = (withQtyPrice: boolean) => {
    const items = collectSelectedItems()
    const fmtPrice = (p: string | number) => Number(p).toLocaleString('de-DE', { maximumFractionDigits: 2 })
    const lines = items.map((i) =>
      withQtyPrice ? `${i.quantity} шт. *  ${i.name} *  ${fmtPrice(i.price)}${i.sign}` : `${i.quantity} шт. *  ${i.name}`,
    )
    if (withQtyPrice && items.length) {
      // Итого по валютам (в выборке могут быть позиции в разных валютах).
      const totals = new Map<string, number>()
      for (const i of items) totals.set(i.sign, (totals.get(i.sign) ?? 0) + (Number(i.price) || 0) * i.quantity)
      const totalText = [...totals.entries()].map(([s, v]) => `${fmtPrice(v)}${s}`).join(' + ')
      lines.push('', `Итого: ${totalText}`)
    }
    void navigator.clipboard?.writeText(lines.join('\n'))
    setActionMenuOpen(false)
  }

  const onBulkOrderStatus = async (statusId: number) => {
    const ids = [...selectedOrders]
    setSelectedOrders(new Set())
    await Promise.all(ids.map((id) => updateOrderStatus(id, statusId).catch(() => {})))
    reload()
  }

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
  // Удаление целых заказов (свёрнутый режим): та же кнопка «Удалить», но сносит
  // заказы целиком через API. Право проверяет бэк (владелец или админ → иначе 403).
  const applyOrderDelete = async () => {
    const ids = [...selectedOrders]
    setDeletingOrders(true)
    const results = await Promise.allSettled(ids.map((id) => deleteOrder(id)))
    setDeletingOrders(false)
    setSelectedOrders(new Set())
    setConfirmDeleteOrders(false)
    const failed = results.filter((r) => r.status === 'rejected').length
    setError(failed ? `Не удалось удалить заказов: ${failed} из ${ids.length} (нет прав — удалять можно только свои).` : null)
    reload()
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    setPage(1)
  }, [statusFilter, methodFilter, establishmentFilter, debouncedSearch, dateFrom, dateTo])

  // Состав строк меняется (фильтры/страница/режим) — сбрасываем отметки, чтобы uid не зависли.
  useEffect(() => {
    setSelected({})
  }, [statusFilter, methodFilter, establishmentFilter, debouncedSearch, dateFrom, dateTo, page])

  const reload = useCallback(() => {
    setLoading(true)
    listOrders({ statusIds: statusFilter, methodIds: methodFilter, establishmentIds: establishmentFilter, search: debouncedSearch, dateFrom, dateTo, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setOrders(res.items)
        setTotals(res.totals ?? [])
        setTotal(res.pagination?.total ?? res.items.length)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [statusFilter, methodFilter, establishmentFilter, debouncedSearch, dateFrom, dateTo, page])

  useEffect(() => {
    if (!creating && editOrder == null) reload()
  }, [creating, editOrder, reload, revision])

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
          <button
            type="button"
            className={styles.dateClear}
            disabled={!hasActiveFilters}
            onClick={resetAllFilters}
            title="Сбросить все фильтры"
            aria-label="Сбросить все фильтры"
          >
            Сброс
          </button>
          <div className={styles.dateFilter}>
            <input
              type="date"
              className={styles.dateInput}
              value={dateFrom}
              max={dateTo || undefined}
              onChange={(e) => setDateFrom(e.target.value)}
              title="Дата от"
              aria-label="Дата от"
            />
            <span className={styles.dateDash}>—</span>
            <input
              type="date"
              className={styles.dateInput}
              value={dateTo}
              min={dateFrom || undefined}
              onChange={(e) => setDateTo(e.target.value)}
              title="Дата до"
              aria-label="Дата до"
            />
          </div>
          <TextInput
            placeholder="Поиск по клиенту или информации…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className={styles.midPanel}>
            {itemStatusOptions.length > 0 && (
              <div className={styles.bulkActions}>
                {orderSelectionCount > 0 ? (
                  <span title={`Статус для ${orderSelectionCount} заказ.`}>
                    <StatusSelect value={null} options={orderStatusOptions} onChange={onBulkOrderStatus} />
                  </span>
                ) : (
                  <span title={selectionCount === 0 ? 'Отметьте позиции галочкой' : `Статус для ${selectionCount} поз.`}>
                    <StatusSelect value={null} options={itemStatusOptions} onChange={onBulkStatus} saving={selectionCount === 0} />
                  </span>
                )}
                <div className={styles.actionWrap}>
                  <button
                    type="button"
                    className={styles.bulkAction}
                    disabled={orderSelectionCount === 0 && selectionCount === 0}
                    onClick={() => setActionMenuOpen((v) => !v)}
                    title="Действия с выбранным"
                  >
                    Действие ▾
                  </button>
                  {actionMenuOpen && (
                    <>
                      <div className={styles.actionBackdrop} onClick={() => setActionMenuOpen(false)} />
                      <div className={styles.actionMenu}>
                        {orderSelectionCount > 0 ? (
                          <button onClick={() => { setActionMenuOpen(false); setConfirmDeleteOrders(true) }}>
                            Удалить заказы ({orderSelectionCount})
                          </button>
                        ) : (
                          <>
                            <button disabled={selectionCount === 0} onClick={() => copyItems(false)}>
                              Скопировать номенклатуру
                            </button>
                            <button disabled={selectionCount === 0} onClick={() => copyItems(true)}>
                              Скопировать с кол-вом и ценой
                            </button>
                            <button className={styles.actionDanger} disabled={selectionCount === 0} onClick={() => { setActionMenuOpen(false); setConfirmDelete(true) }}>
                              Удалить позиции ({selectionCount})
                            </button>
                          </>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
            <span className={styles.expandToggle} title={expandAll ? 'Свернуть все заказы' : 'Развернуть все заказы'}>
              <Switch checked={expandAll} onChange={toggleExpandAll} />
            </span>
          </div>
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
      ) : (
        <OrderSelectionContext.Provider value={selection}>
          <OrdersTable
            orders={orders}
            onOrderPatched={(o) =>
              setOrders((prev) => prev.map((x) => (x.order_id === o.order_id ? o : x)))
            }
            onEdit={setEditOrder}
            expandSignal={{ expanded: expandAll, nonce: expandNonce }}
          />
        </OrderSelectionContext.Provider>
      )}
      </div>

      <div className={styles.grandTotal}>
        <span className={styles.grandTotalLabel}>Итого по всем заказам</span>
        <span className={styles.grandTotalValue}>
          {totals.length > 0
            ? totals.map((t) => `${formatAmount(t.amount)}${t.currency_sign ?? ''}`).join(' · ')
            : '—'}
        </span>
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

      <Modal
        open={confirmDeleteOrders}
        title="Удалить заказы"
        onClose={() => setConfirmDeleteOrders(false)}
        width={420}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDeleteOrders(false)} disabled={deletingOrders}>
              Отмена
            </Button>
            <Button variant="danger" onClick={applyOrderDelete} disabled={deletingOrders}>
              {deletingOrders ? 'Удаление…' : 'Удалить'}
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.5 }}>
          Точно удалить выбранные заказы ({orderSelectionCount}) целиком, вместе с позициями, комментариями и карточкой в чате? Действие необратимо.
        </p>
        <p style={{ margin: '10px 0 0', fontSize: 13, lineHeight: 1.5, color: 'var(--text-muted)' }}>
          Удалить можно только свои заказы; чужие вправе удалять лишь администратор.
        </p>
      </Modal>
    </div>
  )
}
