import { useCallback, useEffect, useState } from 'react'
import { listProducts } from '../../api/endpoints'
import type { Product, ProductSource } from '../../api/types'
import { Button } from '../../ui/Button'
import { TextInput } from '../../ui/Field'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import { ImportXlsxModal } from './ImportXlsxModal'
import { ProductFormModal } from './ProductFormModal'
import { ProductRow } from './ProductRow'
import styles from './ProductsPage.module.css'

const PAGE_SIZE = 50

const SOURCES: { value: ProductSource; label: string }[] = [
  { value: 'price', label: 'Из прайса' },
  { value: 'user', label: 'Созданные' },
]

export function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  // Из прайса CL / созданные пользователями: у вторых себестоимость вбита руками,
  // и в ней бывают рубли, записанные как доллары (16 000 «USD») — смотреть отдельно.
  const [source, setSource] = useState<ProductSource>('price')
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const [creating, setCreating] = useState(false)
  const [importing, setImporting] = useState(false)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, source])

  const load = useCallback(() => {
    setLoading(true)
    listProducts({ search: debouncedSearch, page, pageSize: PAGE_SIZE, source })
      .then((res) => {
        setProducts(res.items)
        setTotal(res.pagination?.total ?? res.items.length)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [debouncedSearch, page, source])

  useEffect(load, [load])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Товары</h1>
        </div>
        <div className={styles.headerActions}>
          <Button variant="secondary" onClick={() => setImporting(true)}>
            📄 Импорт xlsx
          </Button>
          <Button variant="primary" onClick={() => setCreating(true)}>
            + Товар
          </Button>
        </div>
      </header>

      <div className={styles.filters}>
        <div className={styles.switcher} role="tablist">
          {SOURCES.map((s) => (
            <button
              key={s.value}
              type="button"
              role="tab"
              aria-selected={source === s.value}
              className={source === s.value ? styles.switcherActive : undefined}
              onClick={() => setSource(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className={styles.search}>
          <TextInput
            placeholder="Поиск по артикулу или наименованию…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
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

      {source === 'user' && (
        <div className={styles.sourceHint}>
          Товары, заведённые вручную. Цена — себестоимость в USD: если она вбита в рублях (например, 16 000), «Финансы» её
          посчитают как доллары — исправьте здесь.
        </div>
      )}
      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
        {loading ? (
          <div className="dim">Загрузка…</div>
        ) : products.length === 0 ? (
          <div className={styles.empty}>Товаров не найдено</div>
        ) : (
          <div className={styles.list}>
            <div className={[styles.row, styles.headRow, source === 'user' ? styles.rowWithOwner : ''].join(' ')}>
              <span>Артикул</span>
              <span>Наименование</span>
              {source === 'user' && <span>Кем создан</span>}
              <span className={styles.right}>Цена, USD</span>
              <span />
            </div>
            {products.map((p) => (
              <ProductRow
                key={p.product_id}
                product={p}
                showOwner={source === 'user'}
                onChanged={load}
                onError={(m) => setError(m || null)}
              />
            ))}
          </div>
        )}
      </div>

      <ProductFormModal open={creating} product={null} onClose={() => setCreating(false)} onSaved={load} />
      <ImportXlsxModal open={importing} onClose={() => setImporting(false)} onDone={load} />
    </div>
  )
}
