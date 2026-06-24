import type { Currency } from '../../api/types'
import { ButtonGroup } from '../../ui/ButtonGroup'
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
      <div className={styles.head}>
        <div className={styles.name} title={item.name}>
          {item.name}
          {item.article && <span className="dim"> · {item.article}</span>}
        </div>
        <button className={styles.remove} onClick={onRemove} title="Убрать">
          ✕
        </button>
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
          <ButtonGroup
            size="sm"
            value={item.currencyId}
            onChange={(id) => onChange({ currencyId: id })}
            options={currencies.map((c) => ({
              value: c.currency_id,
              label: c.currency_sign || c.currency_name,
            }))}
          />
        )}
      </div>
    </div>
  )
}
