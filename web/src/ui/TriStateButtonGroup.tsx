import styles from './ButtonGroup.module.css'
import type { ChoiceOption } from './ButtonGroup'

type Props<T> = {
  options: ChoiceOption<T>[]
  /** Включённые значения (показывать только их). */
  include: T[]
  /** Исключённые значения (скрыть их, показать остальные). */
  exclude: T[]
  onChange: (include: T[], exclude: T[]) => void
  /** Кол-во колонок в сетке (по умолчанию авто-перенос). */
  columns?: number
  size?: 'md' | 'sm' | 'xs'
}

/**
 * Группа чипов-фильтров с тремя состояниями по клику:
 * нейтрально → включить (показывать только это) → исключить (скрыть это) → нейтрально.
 * «Двойное нажатие» (второй клик) переводит из «включено» в «исключено».
 */
export function TriStateButtonGroup<T extends string | number>({
  options,
  include,
  exclude,
  onChange,
  columns,
  size = 'md',
}: Props<T>) {
  const cycle = (v: T) => {
    if (include.includes(v)) {
      onChange(include.filter((x) => x !== v), [...exclude, v]) // включено → исключаем
    } else if (exclude.includes(v)) {
      onChange(include, exclude.filter((x) => x !== v)) // исключено → сбрасываем
    } else {
      onChange([...include, v], exclude) // нейтрально → включаем
    }
  }
  return (
    <div
      className={styles.group}
      style={columns ? { gridTemplateColumns: `repeat(${columns}, 1fr)` } : undefined}
    >
      {options.map((opt) => {
        const on = include.includes(opt.value)
        const off = exclude.includes(opt.value)
        const title = on
          ? 'Нажмите ещё раз, чтобы исключить'
          : off
            ? 'Нажмите, чтобы сбросить фильтр'
            : 'Нажмите — показать только это; ещё раз — исключить'
        return (
          <button
            key={String(opt.value)}
            type="button"
            title={title}
            className={[styles.chip, on ? styles.active : '', off ? styles.excluded : '', styles[size]].join(' ')}
            onClick={() => cycle(opt.value)}
          >
            {opt.dot && <span className={styles.dot} style={{ background: opt.dot }} />}
            <span className={styles.label}>{off ? `− ${opt.label}` : opt.label}</span>
          </button>
        )
      })}
    </div>
  )
}
