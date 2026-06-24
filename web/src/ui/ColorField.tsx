import { statusColor } from './statusColor'
import styles from './ColorField.module.css'

// Приложение понимает именованные цвета + #hex. Даём оба способа.
const NAMED = ['green', 'orange', 'blue', 'red', 'gray']

export function ColorField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className={styles.wrap}>
      <div className={styles.swatches}>
        {NAMED.map((name) => (
          <button
            key={name}
            type="button"
            className={[styles.swatch, value === name ? styles.active : ''].join(' ')}
            style={{ background: statusColor(name) }}
            title={name}
            onClick={() => onChange(name)}
          />
        ))}
        <span className={styles.preview} style={{ background: statusColor(value) }} />
      </div>
      <input
        className={styles.hex}
        placeholder="или #RRGGBB"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
