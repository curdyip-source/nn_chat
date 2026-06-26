import type { Currency } from '../../api/types'
import { Stepper } from '../../ui/Stepper'
import type { CartItem } from './cart'
import styles from './CartRow.module.css'

type Props = {
  item: CartItem
  currencies: Currency[]
  onChange: (patch: Partial<CartItem>) => void
  onRemove: () => void
}

export function CartRow({ item, currencies, onChange, onRemove }: Props) {
  const priceMissing = !item.price.trim()
  return (
    <div className={styles.row}>
      <div className={styles.name} title={item.name}>
        {item.name}
        {item.article && <span className="dim"> · {item.article}</span>}
      </div>
      <div className={styles.controls}>
        <Stepper value={item.quantity} onChange={(q) => onChange({ quantity: q })} />
        <input
          className={[styles.price, priceMissing ? styles.priceMissing : ''].join(' ')}
          inputMode="decimal"
          placeholder="Цена"
          value={item.price}
          onChange={(e) => onChange({ price: e.target.value.replace(',', '.') })}
        />
        {currencies.length > 0 && (
          <select
            className={styles.currency}
            value={item.currencyId ?? ''}
            onChange={(e) => onChange({ currencyId: Number(e.target.value) })}
          >
            {currencies.map((c) => (
              <option key={c.currency_id} value={c.currency_id}>
                {c.currency_sign || c.currency_name}
              </option>
            ))}
          </select>
        )}
      </div>
      <button className={styles.remove} onClick={onRemove} title="Убрать">
        ✕
      </button>
    </div>
  )
}
