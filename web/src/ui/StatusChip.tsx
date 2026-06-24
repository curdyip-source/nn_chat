import { statusColor } from './statusColor'
import styles from './StatusChip.module.css'

export function StatusChip({ label, color }: { label: string; color: string | null | undefined }) {
  const c = statusColor(color)
  return (
    <span className={styles.chip} style={{ borderColor: `${c}66`, background: `${c}22` }}>
      <span className={styles.dot} style={{ background: c }} />
      {label}
    </span>
  )
}
