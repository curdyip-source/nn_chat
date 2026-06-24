import { useState } from 'react'
import { searchProducts } from '../../api/endpoints'
import type { Product } from '../../api/types'
import { Button } from '../../ui/Button'
import { Field, TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import { SearchSelect } from '../../ui/SearchSelect'
import { Stepper } from '../../ui/Stepper'

type Props = {
  open: boolean
  onClose: () => void
  onAdd: (product: Product, price: string, quantity: number) => void
}

export function AddItemModal({ open, onClose, onAdd }: Props) {
  const [product, setProduct] = useState<Product | null>(null)
  const [price, setPrice] = useState('')
  const [quantity, setQuantity] = useState(1)

  const reset = () => {
    setProduct(null)
    setPrice('')
    setQuantity(1)
  }

  const confirm = () => {
    if (!product) return
    onAdd(product, (Number(price.replace(',', '.')) || 0).toFixed(2), quantity)
    reset()
    onClose()
  }

  return (
    <Modal
      open={open}
      title="Добавить товар"
      onClose={() => {
        reset()
        onClose()
      }}
      width={440}
      footer={
        <>
          <Button variant="ghost" onClick={() => { reset(); onClose() }}>
            Отмена
          </Button>
          <Button variant="primary" disabled={!product} onClick={confirm}>
            Добавить
          </Button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Товар">
          {product ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 10,
                background: 'var(--surface-2)',
                border: '1px solid var(--stroke)',
                borderRadius: 'var(--r-md)',
                padding: '10px 14px',
              }}
            >
              <span>
                {product.product_name}
                <span className="dim"> · {product.product_article}</span>
              </span>
              <button
                onClick={() => setProduct(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: 13 }}
              >
                ✕
              </button>
            </div>
          ) : (
            <SearchSelect<Product>
              autoFocus
              placeholder="Поиск по названию или артикулу…"
              search={(q, signal) => searchProducts(q, signal).then((r) => r.items)}
              getKey={(p) => p.product_id}
              renderItem={(p) => (
                <span>
                  {p.product_name}
                  <span className="dim"> · {p.product_article}</span>
                </span>
              )}
              onSelect={(p) => {
                setProduct(p)
                setPrice(p.product_cost_usd)
              }}
            />
          )}
        </Field>

        <div style={{ display: 'flex', gap: 14, alignItems: 'flex-end' }}>
          <Field label="Количество">
            <Stepper value={quantity} onChange={setQuantity} />
          </Field>
          <div style={{ flex: 1 }}>
            <Field label="Цена">
              <TextInput inputMode="decimal" value={price} placeholder="0.00" onChange={(e) => setPrice(e.target.value)} />
            </Field>
          </div>
        </div>
      </div>
    </Modal>
  )
}
