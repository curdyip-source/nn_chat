import styles from './ButtonGroup.module.css'
import type { ChoiceOption } from './ButtonGroup'

type Props<T> = {
  options: ChoiceOption<T>[]
  /** Выбранные значения (множественный выбор). */
  value: T[]
  onChange: (value: T[]) => void
  /** Кол-во колонок в сетке (по умолчанию авто-перенос). */
  columns?: number
  size?: 'md' | 'sm'
}

/** Группа кнопок-чипов с множественным выбором (тоггл каждого значения). */
export function MultiButtonGroup<T extends string | number>({
  options,
  value,
  onChange,
  columns,
  size = 'md',
}: Props<T>) {
  const toggle = (v: T) => {
    onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v])
  }
  return (
    <div
      className={styles.group}
      style={columns ? { gridTemplateColumns: `repeat(${columns}, 1fr)` } : undefined}
    >
      {options.map((opt) => {
        const active = value.includes(opt.value)
        return (
          <button
            key={String(opt.value)}
            type="button"
            className={[styles.chip, active ? styles.active : '', styles[size]].join(' ')}
            onClick={() => toggle(opt.value)}
          >
            {opt.dot && <span className={styles.dot} style={{ background: opt.dot }} />}
            <span className={styles.label}>{opt.label}</span>
          </button>
        )
      })}
    </div>
  )
}
