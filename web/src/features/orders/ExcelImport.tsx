import { useRef, useState } from 'react'
import * as XLSX from 'xlsx'
import { matchProductsByName, searchProducts } from '../../api/endpoints'
import type { Currency, Product } from '../../api/types'
import { Button } from '../../ui/Button'
import { Modal } from '../../ui/Modal'
import { SearchSelect } from '../../ui/SearchSelect'
import { cartItemFromProduct, newUid, type CartItem } from './cart'
import styles from './ExcelImport.module.css'

// ---- разбор Excel ----

const HEADER_SYNONYMS = {
  name: ['наименование', 'название', 'товар', 'name'],
  quantity: ['количество', 'кол-во', 'колво', 'qty', 'quantity'],
  price: ['цена', 'стоимость', 'price'],
  currency: ['валюта', 'currency'],
}

type RawRow = { name: string; quantity: number; price: string; currency: string }

function normalizeCell(v: unknown): string {
  return String(v ?? '').trim()
}

function parseQuantity(v: unknown): number {
  const n = parseInt(String(v ?? '').replace(/[^\d]/g, ''), 10)
  return Number.isFinite(n) && n > 0 ? n : 1
}

function parsePrice(v: unknown): string {
  const raw = String(v ?? '')
    .replace(/\s/g, '')
    .replace(',', '.')
    .replace(/[^\d.]/g, '')
  const n = Number(raw)
  return Number.isFinite(n) ? n.toFixed(2) : ''
}

function findColumn(headerRow: string[], synonyms: string[]): number {
  return headerRow.findIndex((cell) => synonyms.includes(cell.trim().toLowerCase()))
}

function parseWorkbook(buf: ArrayBuffer): RawRow[] {
  const wb = XLSX.read(buf, { type: 'array' })
  const ws = wb.Sheets[wb.SheetNames[0]]
  if (!ws) return []
  const grid = XLSX.utils.sheet_to_json<unknown[]>(ws, { header: 1, blankrows: false, defval: '' })

  // Ищем строку-заголовок, где есть колонка «Наименование».
  let headerIdx = -1
  let cols = { name: -1, quantity: -1, price: -1, currency: -1 }
  for (let i = 0; i < Math.min(grid.length, 15); i++) {
    const row = grid[i].map((c) => String(c ?? ''))
    const nameCol = findColumn(row, HEADER_SYNONYMS.name)
    if (nameCol !== -1) {
      headerIdx = i
      cols = {
        name: nameCol,
        quantity: findColumn(row, HEADER_SYNONYMS.quantity),
        price: findColumn(row, HEADER_SYNONYMS.price),
        currency: findColumn(row, HEADER_SYNONYMS.currency),
      }
      break
    }
  }
  if (headerIdx === -1) return []

  const rows: RawRow[] = []
  for (let i = headerIdx + 1; i < grid.length; i++) {
    const row = grid[i]
    const name = normalizeCell(row[cols.name])
    if (!name) continue
    rows.push({
      name,
      quantity: cols.quantity >= 0 ? parseQuantity(row[cols.quantity]) : 1,
      price: cols.price >= 0 ? parsePrice(row[cols.price]) : '',
      currency: cols.currency >= 0 ? normalizeCell(row[cols.currency]) : '',
    })
  }
  return rows
}

// ---- сопоставление валюты ----

function resolveCurrencyId(text: string, currencies: Currency[], fallback: number | null): number | null {
  if (!text) return fallback
  const t = text.trim().toLowerCase()
  const hit = currencies.find(
    (c) =>
      c.currency_name.toLowerCase() === t ||
      (c.currency_sign ?? '').toLowerCase() === t,
  )
  return hit ? hit.currency_id : fallback
}

// ---- состояние строки превью ----

type Resolved = {
  raw: RawRow
  uid: string
  product: Product | null
  candidates: Product[]
  currencyId: number | null
}

type Props = {
  open: boolean
  onClose: () => void
  currencies: Currency[]
  defaultCurrencyId: number | null
  onImport: (items: CartItem[]) => void
}

export function ExcelImport({ open, onClose, currencies, defaultCurrencyId, onImport }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [rows, setRows] = useState<Resolved[]>([])
  const [parsing, setParsing] = useState(false)
  const [fileError, setFileError] = useState('')
  const [fileName, setFileName] = useState('')

  const reset = () => {
    setRows([])
    setFileError('')
    setFileName('')
    if (fileRef.current) fileRef.current.value = ''
  }

  const handleFile = async (file: File) => {
    setParsing(true)
    setFileError('')
    setFileName(file.name)
    try {
      const buf = await file.arrayBuffer()
      const raw = parseWorkbook(buf)
      if (raw.length === 0) {
        setRows([])
        setFileError('Не нашли колонку «Наименование» или строки с товарами.')
        return
      }
      const names = [...new Set(raw.map((r) => r.name))]
      const { results } = await matchProductsByName(names)
      const byName = new Map(results.map((r) => [r.query, r]))
      const resolved: Resolved[] = raw.map((r) => {
        const m = byName.get(r.name)
        return {
          raw: r,
          uid: newUid(),
          product: m?.matched ?? null,
          candidates: m?.candidates ?? [],
          currencyId: resolveCurrencyId(r.currency, currencies, defaultCurrencyId),
        }
      })
      setRows(resolved)
    } catch (e) {
      setFileError(e instanceof Error ? e.message : 'Не удалось прочитать файл')
    } finally {
      setParsing(false)
    }
  }

  const setProduct = (uid: string, product: Product | null) =>
    setRows((prev) => prev.map((r) => (r.uid === uid ? { ...r, product } : r)))
  const removeRow = (uid: string) => setRows((prev) => prev.filter((r) => r.uid !== uid))

  const matchedCount = rows.filter((r) => r.product).length
  const unmatchedCount = rows.length - matchedCount

  const doImport = () => {
    const items: CartItem[] = rows
      .filter((r) => r.product)
      .map((r) => {
        const base = cartItemFromProduct(r.product!, r.currencyId)
        return {
          ...base,
          quantity: r.raw.quantity,
          price: r.raw.price || base.price,
        }
      })
    onImport(items)
    reset()
    onClose()
  }

  return (
    <Modal
      open={open}
      title="Импорт товаров из Excel"
      onClose={() => {
        reset()
        onClose()
      }}
      width={720}
      footer={
        rows.length > 0 && (
          <>
            <span className={styles.summary}>
              Сопоставлено {matchedCount} из {rows.length}
              {unmatchedCount > 0 && ` · ${unmatchedCount} без товара будут пропущены`}
            </span>
            <Button variant="ghost" onClick={reset}>
              Сбросить
            </Button>
            <Button variant="primary" disabled={matchedCount === 0} onClick={doImport}>
              Добавить {matchedCount} в заказ
            </Button>
          </>
        )
      }
    >
      {rows.length === 0 ? (
        <div className={styles.dropzone} onClick={() => fileRef.current?.click()}>
          <div className={styles.dropIcon}>⬆️</div>
          <div className={styles.dropTitle}>
            {parsing ? 'Читаем файл…' : 'Выберите .xlsx файл'}
          </div>
          <div className="dim">
            Колонки: <b>Наименование</b>, Количество, Цена, Валюта. Сопоставление — по наименованию.
          </div>
          {fileError && <div className={styles.error}>{fileError}</div>}
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.xls"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void handleFile(f)
            }}
          />
        </div>
      ) : (
        <div className={styles.preview}>
          <div className={styles.fileName}>{fileName}</div>
          <div className={styles.rows}>
            {rows.map((r) => (
              <div
                key={r.uid}
                className={[styles.row, r.product ? styles.ok : styles.bad].join(' ')}
              >
                <div className={styles.rowMain}>
                  <div className={styles.rowName}>{r.raw.name}</div>
                  <div className={styles.rowMeta}>
                    {r.raw.quantity} шт · {r.raw.price || '—'}
                    {r.raw.currency ? ` · ${r.raw.currency}` : ''}
                  </div>
                  {r.product ? (
                    <div className={styles.matched}>
                      ✓ {r.product.product_name}
                      <span className="dim"> · {r.product.product_article}</span>
                    </div>
                  ) : (
                    <div className={styles.pickerWrap}>
                      <SearchSelect<Product>
                        placeholder="Выбрать товар вручную…"
                        search={(q, signal) => searchProducts(q, signal).then((res) => res.items)}
                        getKey={(p) => p.product_id}
                        renderItem={(p) => (
                          <span>
                            {p.product_name}
                            <span className="dim"> · {p.product_article}</span>
                          </span>
                        )}
                        onSelect={(p) => setProduct(r.uid, p)}
                      />
                    </div>
                  )}
                </div>
                <button className={styles.remove} onClick={() => removeRow(r.uid)} title="Убрать">
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  )
}
