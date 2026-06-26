import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { statusColor } from './statusColor'
import styles from './StatusSelect.module.css'

export type StatusOption = {
  id: number
  label: string
  color: string | null
}

type Props = {
  value: number | null | undefined
  options: StatusOption[]
  onChange: (id: number) => void
  saving?: boolean
  size?: 'md' | 'sm'
}

/** Статус-«бабл»: по клику раскрывается список статусов. Выпадашка рендерится
 *  в портал с fixed-позицией, чтобы не обрезалась overflow-родителями (таблица). */
export function StatusSelect({ value, options, onChange, saving, size = 'md' }: Props) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState<{ top?: number; bottom?: number; right: number; maxHeight: number } | null>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const current = options.find((o) => o.id === value)
  const c = statusColor(current?.color)

  const openMenu = () => {
    const rect = triggerRef.current?.getBoundingClientRect()
    if (!rect) return
    const gap = 6
    const margin = 8
    const right = window.innerWidth - rect.right
    const spaceBelow = window.innerHeight - rect.bottom - gap - margin
    const spaceAbove = rect.top - gap - margin
    // Раскрываемся вниз, если снизу хватает места (или его больше, чем сверху),
    // иначе — вверх. maxHeight подгоняем под доступное место, чтобы список не уходил
    // за край экрана и его можно было прокрутить внутри.
    if (spaceBelow >= 220 || spaceBelow >= spaceAbove) {
      setPos({ top: rect.bottom + gap, right, maxHeight: Math.min(320, spaceBelow) })
    } else {
      setPos({ bottom: window.innerHeight - rect.top + gap, right, maxHeight: Math.min(320, spaceAbove) })
    }
    setOpen(true)
  }

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      const t = e.target as Node
      if (triggerRef.current?.contains(t) || dropdownRef.current?.contains(t)) return
      setOpen(false)
    }
    // Скролл закрывает меню — но НЕ внутренний скролл самого списка (capture ловит и его).
    const onScroll = (e: Event) => {
      if (dropdownRef.current?.contains(e.target as Node)) return
      setOpen(false)
    }
    const close = () => setOpen(false)
    document.addEventListener('mousedown', onDocClick)
    window.addEventListener('scroll', onScroll, true)
    window.addEventListener('resize', close)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      window.removeEventListener('scroll', onScroll, true)
      window.removeEventListener('resize', close)
    }
  }, [open])

  return (
    <div className={styles.root}>
      <button
        ref={triggerRef}
        type="button"
        className={[styles.chip, size === 'sm' ? styles.sm : ''].join(' ')}
        style={{ borderColor: `${c}66`, background: `${c}22` }}
        onClick={() => (open ? setOpen(false) : openMenu())}
        disabled={saving}
      >
        <span className={styles.dot} style={{ background: c }} />
        {current?.label ?? 'Статус'}
        <span className={styles.caret}>▾</span>
      </button>
      {open &&
        pos &&
        createPortal(
          <div
            ref={dropdownRef}
            className={styles.dropdown}
            style={{
              position: 'fixed',
              // Явно задаём обе оси: иначе при раскрытии вверх остаётся top из CSS-класса
              // (top: calc(100% + 6px)) и fixed-элемент сплющивается между top и bottom.
              top: pos.top != null ? pos.top : 'auto',
              bottom: pos.bottom != null ? pos.bottom : 'auto',
              right: pos.right,
              maxHeight: pos.maxHeight,
            }}
          >
            {options.map((o) => (
              <button
                key={o.id}
                type="button"
                className={[styles.option, o.id === value ? styles.active : ''].join(' ')}
                onClick={() => {
                  setOpen(false)
                  if (o.id !== value) onChange(o.id)
                }}
              >
                <span className={styles.dot} style={{ background: statusColor(o.color) }} />
                {o.label}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </div>
  )
}
