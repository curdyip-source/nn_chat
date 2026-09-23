import { useEffect, useState } from 'react'
import {
  bulkSetOrderItemCostRate,
  correctOrderItemCost,
  fetchExchangeRates,
  fetchExpenseCategories,
  fetchExpenses,
  fetchFinanceSummary,
  overrideExchangeRate,
  saveExpense,
  saveExpenseCategory,
  deleteExpense,
} from '../../api/endpoints'
import type { ExchangeRate, FinanceExpense, FinanceExpenseCategory, FinancePeriodOverview, OrderItemForReview } from '../../api/types'
import { formatAmount } from '../../lib/format'
import { Button } from '../../ui/Button'
import { ButtonGroup } from '../../ui/ButtonGroup'
import { Checkbox } from '../../ui/Checkbox'
import { Field, TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import styles from './FinancePage.module.css'

type Tab = 'overview' | 'expenses' | 'categories' | 'rate'

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Обзор' },
  { key: 'expenses', label: 'Расходы' },
  { key: 'categories', label: 'Категории' },
  { key: 'rate', label: 'Курс' },
]

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

function toIsoDate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// По умолчанию — текущий месяц целиком, как «дефолтный» диапазон в «Заказах».
function currentMonthStart(): string {
  const now = new Date()
  return toIsoDate(new Date(now.getFullYear(), now.getMonth(), 1))
}

function currentMonthEnd(): string {
  const now = new Date()
  return toIsoDate(new Date(now.getFullYear(), now.getMonth() + 1, 0))
}

function money(value: string | number): string {
  return formatAmount(Number(value))
}

function shortDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

const PAGE_SIZE = 100

export function FinancePage() {
  const [tab, setTab] = useState<Tab>('overview')
  const [dateFrom, setDateFrom] = useState(currentMonthStart())
  const [dateTo, setDateTo] = useState(currentMonthEnd())

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Финансы</h1>
      </header>

      <div className={styles.tabsRow}>
        <div className={styles.tabsGroup}>
          <ButtonGroup size="sm" value={tab} onChange={(t) => t && setTab(t)} options={TABS.map((t) => ({ value: t.key, label: t.label }))} />
        </div>
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
      </div>

      <div className={styles.scroll}>
        {tab === 'overview' && <OverviewTab dateFrom={dateFrom} dateTo={dateTo} />}
        {tab === 'expenses' && (
          <div className={styles.tabScroll}>
            <ExpensesTab dateFrom={dateFrom} dateTo={dateTo} />
          </div>
        )}
        {tab === 'categories' && (
          <div className={styles.tabScroll}>
            <CategoriesTab />
          </div>
        )}
        {tab === 'rate' && (
          <div className={styles.tabScroll}>
            <RateTab dateFrom={dateFrom} dateTo={dateTo} />
          </div>
        )}
      </div>
    </div>
  )
}

function useSaver<T>(fn: () => Promise<T>, onSaved: () => void) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const run = async () => {
    setError('')
    setBusy(true)
    try {
      await fn()
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить')
    } finally {
      setBusy(false)
    }
  }
  return { busy, error, run }
}

function OverviewTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const [data, setData] = useState<FinancePeriodOverview | null>(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [reviewItem, setReviewItem] = useState<OrderItemForReview | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkOpen, setBulkOpen] = useState(false)

  const reload = (targetPage = page) => {
    fetchFinanceSummary(dateFrom, dateTo, targetPage, PAGE_SIZE)
      .then((r) => {
        setData(r)
        setSelected(new Set())
        setError('')
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Не удалось загрузить'))
  }

  useEffect(() => {
    setData(null)
    setSelected(new Set())
    setPage(1)
    // Пока «дата от» и «дата до» не согласованы (пользователь ещё не успел
    // поправить второе поле), бэкенд ответит 422 — не залипаем на этой ошибке
    // навсегда, а просто ждём следующего валидного сочетания дат.
    if (dateTo < dateFrom) {
      setError('')
      return
    }
    fetchFinanceSummary(dateFrom, dateTo, 1, PAGE_SIZE)
      .then((r) => {
        setData(r)
        setError('')
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Не удалось загрузить'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateFrom, dateTo])

  useEffect(() => {
    if (page === 1) return
    reload(page)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  if (error) return <div className={styles.error}>{error}</div>
  if (!data) return <div className={styles.dim}>Загрузка…</div>

  const toggleSelected = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const allSelected = data.items.length > 0 && selected.size === data.items.length
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(data.items.map((i) => i.order_item_id)))

  return (
    <div className={styles.overviewRoot}>
      <div className={styles.overviewFixed}>
        <div className={styles.cards}>
          <Card label="Выручка" value={money(data.revenue)} />
          <Card label="Себестоимость" value={money(data.cost_rub)} />
          <Card label="Валовая прибыль" value={money(data.gross_profit)} />
          <Card label="Расходы" value={money(data.expenses_total)} />
          <Card label="Чистая прибыль" value={money(data.net_profit)} emphasis />
        </div>

        <div className={styles.itemsHeader}>
          <div className={styles.groupTitle}>
            Отгруженные товары месяца ({data.items_count}, без себестоимости — {data.missing_cost_count})
          </div>
          {data.items.length > 0 && (
            <div className={styles.itemsHeaderActions}>
              <label className={styles.selectAll}>
                <Checkbox checked={allSelected} onChange={toggleAll} />
                <span>Выбрать все на странице</span>
              </label>
              <Button variant="ghost" disabled={selected.size === 0} onClick={() => setBulkOpen(true)}>
                Изменить курс ({selected.size})
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className={styles.itemsScrollArea}>
        {data.items.length === 0 && <div className={styles.dim}>За этот месяц отгруженных товаров пока нет.</div>}
        <div className={styles.list}>
          {data.items.map((item) => (
            <ShippedItemRow
              key={item.order_item_id}
              item={item}
              checked={selected.has(item.order_item_id)}
              onToggle={() => toggleSelected(item.order_item_id)}
              onOpen={() => setReviewItem(item)}
            />
          ))}
        </div>
      </div>

      {data.pagination.total_pages > 1 && (
        <div className={styles.overviewFixed}>
          <div className={styles.pager}>
            <Button variant="ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              ← Назад
            </Button>
            <span className={styles.dim}>
              Стр. {data.pagination.page} из {data.pagination.total_pages}
            </span>
            <Button variant="ghost" disabled={page >= data.pagination.total_pages} onClick={() => setPage((p) => p + 1)}>
              Вперёд →
            </Button>
          </div>
        </div>
      )}

      {bulkOpen && (
        <BulkRateModal
          itemIds={Array.from(selected)}
          onClose={() => setBulkOpen(false)}
          onSaved={() => {
            setBulkOpen(false)
            reload()
          }}
        />
      )}

      {reviewItem && (
        <CostCorrectionModal
          item={reviewItem}
          onClose={() => setReviewItem(null)}
          onSaved={() => {
            setReviewItem(null)
            reload()
          }}
        />
      )}
    </div>
  )
}

function ShippedItemRow({
  item,
  checked,
  onToggle,
  onOpen,
}: {
  item: OrderItemForReview
  checked: boolean
  onToggle: () => void
  onOpen: () => void
}) {
  const hasCost = item.order_item_cost_rate !== null
  const isUsd = item.order_item_currency_name === 'USD'
  return (
    <div className={styles.itemRow}>
      <Checkbox checked={checked} onChange={onToggle} />
      <button className={styles.rowMain} onClick={onOpen}>
        <span className={styles.itemLine1}>
          <span className={hasCost ? styles.dot : styles.dotMissing} title={hasCost ? 'Себестоимость есть' : 'Себестоимость не проставлена'} />
          <span className={styles.dim}>{shortDate(item.order_item_shipped_at)}</span>
          <span className={styles.dim}>· Заказ №{item.order_item_order_id}</span>
          <span>· {item.order_item_name}</span>
          <span className={styles.dim}>· {item.order_item_quantity} шт.</span>
          <span className={styles.priceBold}>
            · {money(item.order_item_price)} {item.order_item_currency_name}
          </span>
        </span>
        <span className={styles.itemLine2}>
          {item.order_item_cost_usd !== null ? (
            <>себестоимость {money(item.order_item_cost_usd)} USD</>
          ) : (
            <>себестоимость не задана</>
          )}
          {hasCost &&
            (isUsd && item.order_item_margin_usd !== null ? (
              <>
                {' '}
                · маржа {money(item.order_item_margin_usd)} USD × {money(item.order_item_cost_rate ?? '0')} = {money(item.order_item_margin ?? '0')} ₽
              </>
            ) : (
              <> · маржа {money(item.order_item_margin ?? '0')} ₽</>
            ))}
          {hasCost && item.order_item_quantity > 1 && (
            <>
              {' '}
              · итого за {item.order_item_quantity} шт.:{' '}
              <span className={styles.marginTotal}>
                {isUsd && item.order_item_margin_usd_total !== null && <>{money(item.order_item_margin_usd_total)} USD = </>}
                {money(item.order_item_margin_total ?? '0')} ₽
              </span>
            </>
          )}
        </span>
      </button>
    </div>
  )
}

function Card({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <div className={[styles.card, emphasis ? styles.cardEmphasis : ''].join(' ')}>
      <div className={styles.cardLabel}>{label}</div>
      <div className={styles.cardValue}>{value} ₽</div>
    </div>
  )
}

function CostCorrectionModal({ item, onClose, onSaved }: { item: OrderItemForReview; onClose: () => void; onSaved: () => void }) {
  const [usd, setUsd] = useState(item.order_item_cost_usd ?? '')
  const [rate, setRate] = useState(item.order_item_cost_rate ?? '')
  const { busy, error, run } = useSaver(
    () => correctOrderItemCost(item.order_item_id, { order_item_cost_usd: usd.trim() || null, order_item_cost_rate: rate.trim() || null }),
    onSaved,
  )
  return (
    <Modal
      open
      title={item.order_item_name}
      onClose={onClose}
      width={420}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="primary" loading={busy} onClick={run}>
            Сохранить
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <Field label="Себестоимость, USD">
          <TextInput value={usd} onChange={(e) => setUsd(e.target.value)} placeholder="0.00" autoFocus />
        </Field>
        <Field label="Курс USD/RUB" hint="На момент заказа курса могло не быть — впишите вручную">
          <TextInput value={rate} onChange={(e) => setRate(e.target.value)} placeholder="0.0000" />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function BulkRateModal({ itemIds, onClose, onSaved }: { itemIds: number[]; onClose: () => void; onSaved: () => void }) {
  const [rate, setRate] = useState('')
  const { busy, error, run } = useSaver(() => bulkSetOrderItemCostRate(itemIds, rate.trim()), onSaved)
  return (
    <Modal
      open
      title={`Курс для ${itemIds.length} ${itemIds.length === 1 ? 'позиции' : 'позиций'}`}
      onClose={onClose}
      width={400}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="primary" loading={busy} disabled={!rate.trim()} onClick={run}>
            Применить
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <Field label="Курс USD/RUB" hint="Проставится на все отмеченные позиции разом (себестоимость в USD не меняется)">
          <TextInput value={rate} onChange={(e) => setRate(e.target.value)} placeholder="0.0000" autoFocus />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function ExpensesTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const [items, setItems] = useState<FinanceExpense[] | null>(null)
  const [categories, setCategories] = useState<FinanceExpenseCategory[]>([])
  const [edit, setEdit] = useState<FinanceExpense | null | 'new'>(null)
  const [error, setError] = useState('')

  const reload = () => {
    fetchExpenses(dateFrom, dateTo)
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : 'Не удалось загрузить'))
  }

  useEffect(() => {
    setItems(null)
    reload()
    fetchExpenseCategories().then((r) => setCategories(r.items))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateFrom, dateTo])

  const remove = async (id: number) => {
    if (!window.confirm('Удалить расход?')) return
    try {
      await deleteExpense(id)
      reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось удалить')
    }
  }

  return (
    <div>
      <header className={styles.subHeader}>
        <Button variant="primary" onClick={() => setEdit('new')} disabled={categories.length === 0}>
          + Добавить расход
        </Button>
        {categories.length === 0 && <span className={styles.dim}>Сначала добавьте категорию расходов</span>}
      </header>
      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.list}>
        {(items ?? []).map((e) => (
          <div key={e.finance_expense_id} className={styles.expenseRow}>
            <button className={styles.expenseRowMain} onClick={() => setEdit(e)}>
              <span className={styles.dim}>{shortDate(e.finance_expense_period)}</span>
              <span>· {e.finance_expense_category_name ?? '—'}</span>
              {e.finance_expense_note && <span className={styles.expenseNote}>· {e.finance_expense_note}</span>}
              <span className={styles.expenseAmountInline}>{money(e.finance_expense_amount)} ₽</span>
            </button>
            <button className={styles.deleteBtn} onClick={() => remove(e.finance_expense_id)} title="Удалить">
              ✕
            </button>
          </div>
        ))}
        {items && items.length === 0 && <div className={styles.dim}>Расходов за выбранный период пока нет.</div>}
      </div>

      {edit !== null && (
        <ExpenseModal
          item={edit === 'new' ? null : edit}
          defaultPeriod={dateFrom}
          categories={categories}
          onClose={() => setEdit(null)}
          onSaved={() => {
            setEdit(null)
            reload()
          }}
        />
      )}
    </div>
  )
}

function ExpenseModal({
  item,
  defaultPeriod,
  categories,
  onClose,
  onSaved,
}: {
  item: FinanceExpense | null
  defaultPeriod: string
  categories: FinanceExpenseCategory[]
  onClose: () => void
  onSaved: () => void
}) {
  const [categoryId, setCategoryId] = useState(item?.finance_expense_category_id ?? categories[0]?.finance_expense_category_id ?? 0)
  const [amount, setAmount] = useState(item?.finance_expense_amount ?? '')
  const [note, setNote] = useState(item?.finance_expense_note ?? '')
  // Точная дата расхода — своя, отдельная от диапазона-фильтра сверху: при
  // редактировании берём дату самого расхода (иначе правка молча переносила бы его
  // на дату из текущего фильтра), при создании — начало выбранного диапазона.
  const [expenseDate, setExpenseDate] = useState(item?.finance_expense_period ?? defaultPeriod)
  const { busy, error, run } = useSaver(
    () =>
      saveExpense(item?.finance_expense_id ?? null, {
        finance_expense_category_id: categoryId,
        finance_expense_period: expenseDate,
        finance_expense_amount: amount.trim(),
        finance_expense_note: note.trim() || null,
      }),
    onSaved,
  )
  return (
    <Modal
      open
      title={item ? 'Расход' : 'Новый расход'}
      onClose={onClose}
      width={440}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="primary" loading={busy} disabled={!amount.trim() || !categoryId} onClick={run}>
            Сохранить
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <Field label="Дата">
          <input type="date" className={styles.select} value={expenseDate} onChange={(e) => setExpenseDate(e.target.value)} />
        </Field>
        <Field label="Категория">
          <select className={styles.select} value={categoryId} onChange={(e) => setCategoryId(Number(e.target.value))}>
            {categories.map((c) => (
              <option key={c.finance_expense_category_id} value={c.finance_expense_category_id}>
                {c.finance_expense_category_name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Сумма, ₽">
          <TextInput value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" autoFocus />
        </Field>
        <Field label="Заметка">
          <TextInput value={note} onChange={(e) => setNote(e.target.value)} placeholder="Необязательно" />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function CategoriesTab() {
  const [items, setItems] = useState<FinanceExpenseCategory[] | null>(null)
  const [edit, setEdit] = useState<FinanceExpenseCategory | null | 'new'>(null)

  const reload = () => fetchExpenseCategories().then((r) => setItems(r.items))

  useEffect(() => {
    reload()
  }, [])

  return (
    <div>
      <header className={styles.subHeader}>
        <Button variant="primary" onClick={() => setEdit('new')}>
          + Добавить категорию
        </Button>
      </header>
      <div className={styles.list}>
        {(items ?? []).map((c) => (
          <button key={c.finance_expense_category_id} className={styles.row} onClick={() => setEdit(c)}>
            {c.finance_expense_category_name}
          </button>
        ))}
      </div>

      {edit !== null && (
        <CategoryModal
          item={edit === 'new' ? null : edit}
          onClose={() => setEdit(null)}
          onSaved={() => {
            setEdit(null)
            reload()
          }}
        />
      )}
    </div>
  )
}

function CategoryModal({ item, onClose, onSaved }: { item: FinanceExpenseCategory | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(item?.finance_expense_category_name ?? '')
  const { busy, error, run } = useSaver(
    () => saveExpenseCategory(item?.finance_expense_category_id ?? null, { finance_expense_category_name: name.trim() }),
    onSaved,
  )
  return (
    <Modal
      open
      title={item ? 'Категория' : 'Новая категория'}
      onClose={onClose}
      width={400}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="primary" loading={busy} disabled={!name.trim()} onClick={run}>
            Сохранить
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <Field label="Название">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} autoFocus placeholder="Зарплата" />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}

function RateTab({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const [items, setItems] = useState<ExchangeRate[] | null>(null)
  const [edit, setEdit] = useState<ExchangeRate | null>(null)
  const [error, setError] = useState('')

  const reload = () => {
    fetchExchangeRates(dateFrom, dateTo)
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : 'Не удалось загрузить'))
  }

  useEffect(() => {
    setItems(null)
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateFrom, dateTo])

  return (
    <div>
      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.list}>
        {(items ?? []).map((r) => (
          <button key={r.exchange_rate_id} className={styles.row} onClick={() => setEdit(r)}>
            <span>{r.exchange_rate_date}</span>
            <span>
              {money(r.exchange_rate_value)} ₽{' '}
              <span className={styles.dim}>{r.exchange_rate_source === 'manual' ? '(вручную)' : '(ЦБ)'}</span>
            </span>
          </button>
        ))}
        {items && items.length === 0 && <div className={styles.dim}>За выбранный период курсов пока нет.</div>}
      </div>

      {edit && (
        <RateModal
          item={edit}
          onClose={() => setEdit(null)}
          onSaved={() => {
            setEdit(null)
            reload()
          }}
        />
      )}
    </div>
  )
}

function RateModal({ item, onClose, onSaved }: { item: ExchangeRate; onClose: () => void; onSaved: () => void }) {
  const [value, setValue] = useState(item.exchange_rate_value)
  const { busy, error, run } = useSaver(() => overrideExchangeRate(item.exchange_rate_date, value.trim()), onSaved)
  return (
    <Modal
      open
      title={`Курс на ${item.exchange_rate_date}`}
      onClose={onClose}
      width={380}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="primary" loading={busy} disabled={!value.trim()} onClick={run}>
            Сохранить
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        <Field label="Рублей за 1 USD" hint="Ручная коррекция приоритетнее автоматического курса ЦБ">
          <TextInput value={value} onChange={(e) => setValue(e.target.value)} autoFocus />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}
