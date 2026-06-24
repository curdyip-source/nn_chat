import styles from './Stepper.module.css'

type Props = {
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
}

export function Stepper({ value, onChange, min = 1, max = 9999 }: Props) {
  const clamp = (n: number) => Math.max(min, Math.min(max, n))
  return (
    <div className={styles.stepper}>
      <button
        type="button"
        className={styles.btn}
        onClick={() => onChange(clamp(value - 1))}
        disabled={value <= min}
      >
        −
      </button>
      <input
        className={styles.value}
        type="number"
        inputMode="numeric"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(clamp(Number(e.target.value) || min))}
      />
      <button
        type="button"
        className={styles.btn}
        onClick={() => onChange(clamp(value + 1))}
        disabled={value >= max}
      >
        +
      </button>
    </div>
  )
}
