import styles from './Checkbox.module.css'

type Props = {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  title?: string
}

/** Аккуратный квадратный чекбокс на кнопке (без нативного input). */
export function Checkbox({ checked, onChange, disabled, title }: Props) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      disabled={disabled}
      title={title}
      className={[styles.box, checked ? styles.checked : ''].join(' ')}
      onClick={() => onChange(!checked)}
    >
      {checked && (
        <svg viewBox="0 0 12 12" width="8" height="8" aria-hidden>
          <path d="M2.5 6.2l2.2 2.3 4.8-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </button>
  )
}
