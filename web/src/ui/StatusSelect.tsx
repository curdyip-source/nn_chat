import { useEffect, useRef, useState } from 'react'
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

/** Статус-«бабл»: по клику раскрывается список статусов с цветными точками. */
export function StatusSelect({ value, options, onChange, saving, size = 'md' }: Props) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const current = options.find((o) => o.id === value)
  const c = statusColor(current?.color)

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  return (
    <div className={styles.root} ref={rootRef}>
      <button
        type="button"
        className={[styles.chip, size === 'sm' ? styles.sm : ''].join(' ')}
        style={{ borderColor: `${c}66`, background: `${c}22` }}
        onClick={() => setOpen((v) => !v)}
        disabled={saving}
      >
        <span className={styles.dot} style={{ background: c }} />
        {current?.label ?? 'Статус'}
        <span className={styles.caret}>▾</span>
      </button>
      {open && (
        <div className={styles.dropdown}>
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
        </div>
      )}
    </div>
  )
}
