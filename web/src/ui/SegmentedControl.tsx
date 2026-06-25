import type { CSSProperties } from 'react'
import styles from './SegmentedControl.module.css'

type Option<T> = { value: T; label: string }

type Props<T> = {
  options: Option<T>[]
  value: T
  onChange: (value: T) => void
}

/** iOS-style сегментный переключатель со скользящим бегунком. */
export function SegmentedControl<T extends string | number>({ options, value, onChange }: Props<T>) {
  const activeIndex = Math.max(0, options.findIndex((o) => o.value === value))
  const vars = { '--seg-count': options.length, '--seg-active': activeIndex } as CSSProperties
  return (
    <div
      className={styles.root}
      style={{ ...vars, gridTemplateColumns: `repeat(${options.length}, 1fr)` }}
    >
      <span className={styles.thumb} aria-hidden />
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          className={[styles.seg, o.value === value ? styles.active : ''].join(' ')}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
