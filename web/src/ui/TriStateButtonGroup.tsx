import styles from './ButtonGroup.module.css'
import type { ChoiceOption } from './ButtonGroup'

type Props<T> = {
  options: ChoiceOption<T>[]
  /** Выбранные значения (показывать только их; пусто = без фильтра). */
  value: T[]
  onChange: (value: T[]) => void
  /** Кол-во колонок в сетке (по умолчанию авто-перенос). */
  columns?: number
  size?: 'md' | 'sm' | 'xs'
}

/**
 * Группа чипов-фильтров с «умным» циклом по клику:
 * нейтрально → только это (активно) → все, КРОМЕ этого (активны остальные) → сброс.
 * «Исключение» показывается не отдельным стилем, а подсветкой всех прочих как активных.
 */
export function TriStateButtonGroup<T extends string | number>({
  options,
  value,
  onChange,
  columns,
  size = 'md',
}: Props<T>) {
  const all = options.map((o) => o.value)
  const cycle = (v: T) => {
    const isOnly = value.length === 1 && value[0] === v // сейчас «только v»
    const isAllBut = !value.includes(v) && all.length > 1 && value.length === all.length - 1 // «все кроме v»
    if (isOnly) {
      onChange(all.filter((x) => x !== v)) // только v → все, кроме v
    } else if (isAllBut) {
      onChange([]) // все кроме v → сброс
    } else if (value.includes(v)) {
      onChange(value.filter((x) => x !== v)) // обычное снятие
    } else {
      onChange([...value, v]) // обычное добавление
    }
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
            title="Клик — только это; ещё раз — все, кроме этого"
            className={[styles.chip, active ? styles.active : '', styles[size]].join(' ')}
            onClick={() => cycle(opt.value)}
          >
            {opt.dot && <span className={styles.dot} style={{ background: opt.dot }} />}
            <span className={styles.label}>{opt.label}</span>
          </button>
        )
      })}
    </div>
  )
}
