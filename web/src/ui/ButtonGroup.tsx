import styles from './ButtonGroup.module.css'

export type ChoiceOption<T> = {
  value: T
  label: string
  /** Цветовая точка слева (для статусов). */
  dot?: string
}

type Props<T> = {
  options: ChoiceOption<T>[]
  value: T | null
  onChange: (value: T | null) => void
  /** Разрешить повторным кликом снять выбор. */
  deselectable?: boolean
  /** Кол-во колонок в сетке (по умолчанию авто-перенос). */
  columns?: number
  size?: 'md' | 'sm'
}

export function ButtonGroup<T extends string | number>({
  options,
  value,
  onChange,
  deselectable = false,
  columns,
  size = 'md',
}: Props<T>) {
  return (
    <div
      className={styles.group}
      style={columns ? { gridTemplateColumns: `repeat(${columns}, 1fr)` } : undefined}
    >
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={String(opt.value)}
            type="button"
            className={[styles.chip, active ? styles.active : '', styles[size]].join(' ')}
            onClick={() => onChange(active && deselectable ? null : opt.value)}
          >
            {opt.dot && (
              <span className={styles.dot} style={{ background: opt.dot }} />
            )}
            <span className={styles.label}>{opt.label}</span>
          </button>
        )
      })}
    </div>
  )
}
