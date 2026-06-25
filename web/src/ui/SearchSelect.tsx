import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useDebouncedValue } from './useDebouncedValue'
import styles from './SearchSelect.module.css'

type Props<T> = {
  placeholder?: string
  /** Минимум символов для запуска поиска. */
  minChars?: number
  search: (query: string, signal: AbortSignal) => Promise<T[]>
  getKey: (item: T) => string | number
  renderItem: (item: T) => ReactNode
  onSelect: (item: T) => void
  /** Управляемый режим: текст поля принадлежит родителю (поле = значение). */
  value?: string
  onValueChange?: (value: string) => void
  /** Очищать поле после выбора (только в неуправляемом режиме). */
  clearOnSelect?: boolean
  /** Слот, который показывается, когда поиск ничего не нашёл (например «создать товар»). */
  renderEmptyAction?: (query: string) => ReactNode
  autoFocus?: boolean
  /**
   * Вставка списка: если в буфере 2+ непустых строк, вместо ввода в поле
   * вызывается этот колбэк со списком строк (например, для массового добавления товаров).
   */
  onBulkPaste?: (lines: string[]) => void
}

export function SearchSelect<T>({
  placeholder = 'Поиск…',
  minChars = 2,
  search,
  getKey,
  renderItem,
  onSelect,
  value,
  onValueChange,
  clearOnSelect = true,
  renderEmptyAction,
  autoFocus,
  onBulkPaste,
}: Props<T>) {
  const controlled = value !== undefined
  const [internalQuery, setInternalQuery] = useState('')
  const query = controlled ? value! : internalQuery
  const setQuery = (v: string) => (controlled ? onValueChange?.(v) : setInternalQuery(v))

  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<T[]>([])
  const [loading, setLoading] = useState(false)
  const debounced = useDebouncedValue(query.trim(), 220)
  const skipNextSearch = useRef(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // После выбора родитель подставляет текст (имя контакта) — не открываем поиск заново.
    if (skipNextSearch.current) {
      skipNextSearch.current = false
      return
    }
    if (debounced.length < minChars) {
      setItems([])
      setLoading(false)
      setOpen(false)
      return
    }
    const ctrl = new AbortController()
    setLoading(true)
    search(debounced, ctrl.signal)
      .then((res) => {
        setItems(res)
        setOpen(true)
      })
      .catch((e) => {
        if (e?.name !== 'AbortError') setItems([])
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [debounced, minChars, search])

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const handleSelect = (item: T) => {
    onSelect(item)
    if (controlled) skipNextSearch.current = true
    else if (clearOnSelect) setInternalQuery('')
    setOpen(false)
  }

  const showDropdown = open && debounced.length >= minChars
  const showEmpty = showDropdown && !loading && items.length === 0

  return (
    <div className={styles.root} ref={rootRef}>
      <input
        className={styles.input}
        value={query}
        placeholder={placeholder}
        autoFocus={autoFocus}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => !skipNextSearch.current && debounced.length >= minChars && setOpen(true)}
        onPaste={(e) => {
          if (!onBulkPaste) return
          const lines = e.clipboardData
            .getData('text')
            .split(/\r?\n/)
            .map((l) => l.trim())
            .filter(Boolean)
          if (lines.length >= 2) {
            e.preventDefault()
            setQuery('')
            setOpen(false)
            onBulkPaste(lines)
          }
        }}
      />
      {loading && <span className={styles.loader} />}
      {showDropdown && (
        <div className={styles.dropdown}>
          {items.map((item) => (
            <button
              key={getKey(item)}
              type="button"
              className={styles.option}
              onClick={() => handleSelect(item)}
            >
              {renderItem(item)}
            </button>
          ))}
          {showEmpty && (
            <div className={styles.empty}>
              {renderEmptyAction ? renderEmptyAction(query.trim()) : 'Ничего не найдено'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
