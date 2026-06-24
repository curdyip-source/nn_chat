import { useCallback, useEffect, useState } from 'react'
import { listProducts } from '../../api/endpoints'
import type { Product } from '../../api/types'
import { Button } from '../../ui/Button'
import { TextInput } from '../../ui/Field'
import { useDebouncedValue } from '../../ui/useDebouncedValue'
import { formatAmount } from '../../lib/format'
import { ImportXlsxModal } from './ImportXlsxModal'
import { ProductFormModal } from './ProductFormModal'
import styles from './ProductsPage.module.css'

const PAGE_SIZE = 50

export function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const [editing, setEditing] = useState<Product | null>(null)
  const [creating, setCreating] = useState(false)
  const [importing, setImporting] = useState(false)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // Сброс на первую страницу при изменении поиска.
  useEffect(() => {
    setPage(1)
  }, [debouncedSearch])

  const load = useCallback(() => {
    setLoading(true)
    listProducts({ search: debouncedSearch, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setProducts(res.items)
        setTotal(res.pagination?.total ?? res.items.length)
        setError(null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [debouncedSearch, page])

  useEffect(load, [load])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Товары</h1>
          <p className="muted">Номенклатура{total ? ` · ${total}` : ''}: поиск, создание и импорт</p>
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
        <TextInput
          placeholder="Поиск по артикулу или наименованию…"
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

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.scroll}>
        {loading ? (
          <div className="dim">Загрузка…</div>
        ) : products.length === 0 ? (
          <div className={styles.empty}>Товаров не найдено</div>
        ) : (
          <div className={styles.list}>
            <div className={[styles.row, styles.headRow].join(' ')}>
              <span>Артикул</span>
              <span>Наименование</span>
              <span className={styles.right}>Цена, USD</span>
            </div>
            {products.map((p) => (
              <button key={p.product_id} className={styles.row} onClick={() => setEditing(p)}>
                <span className={styles.article}>{p.product_article}</span>
                <span className={styles.name}>{p.product_name}</span>
                <span className={styles.right}>{formatAmount(Number(p.product_cost_usd) || 0)}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <ProductFormModal open={creating} product={null} onClose={() => setCreating(false)} onSaved={load} />
      <ProductFormModal open={editing != null} product={editing} onClose={() => setEditing(null)} onSaved={load} />
      <ImportXlsxModal open={importing} onClose={() => setImporting(false)} onDone={load} />
    </div>
  )
}
