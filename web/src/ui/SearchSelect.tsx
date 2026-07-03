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
  // Ищем/открываем выпадашку только в ответ на ручной ввод. Программная подстановка
  // текста (выбор контакта подставляет его имя; ремоунт при смене вкладки) не должна
  // заново запускать поиск — иначе окно с результатами всплывает само собой.
  const typingRef = useRef(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!typingRef.current) return
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
    typingRef.current = false
    // WebKit/Safari: выбор синхронно подменяет DOM (выпадашка закрывается, на месте
    // инпута появляется чип/новый элемент). На один физический клик Safari при этом
    // диспатчит ВТОРОЙ, «фантомный» click по элементу, который оказался под курсором
    // после ре-рендера (например по кнопке удаления только что выбранного товара) —
    // он тут же сбрасывал выбор. Глотаем ровно один следующий click за текущий тик.
    const swallow = (e: MouseEvent) => {
      e.stopPropagation()
      e.preventDefault()
    }
    document.addEventListener('click', swallow, true)
    setTimeout(() => document.removeEventListener('click', swallow, true), 0)

    onSelect(item)
    if (!controlled && clearOnSelect) setInternalQuery('')
    setItems([])
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
        onChange={(e) => {
          typingRef.current = true
          setQuery(e.target.value)
        }}
        onFocus={() => debounced.length >= minChars && items.length > 0 && setOpen(true)}
        onPaste={(e) => {
          if (!onBulkPaste) return
          const lines = e.clipboardData
            .getData('text')
            .split(/\r?\n/)
            .map((l) => l.trim())
            .filter(Boolean)
          if (lines.length >= 2) {
            e.preventDefault()
            typingRef.current = false
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
