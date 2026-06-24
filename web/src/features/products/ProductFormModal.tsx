import { useEffect, useState } from 'react'
import { createProduct, updateProduct } from '../../api/endpoints'
import type { Product } from '../../api/types'
import { Button } from '../../ui/Button'
import { Field, TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'

type Props = {
  open: boolean
  product: Product | null // null -> создание
  onClose: () => void
  onSaved: () => void
}

export function ProductFormModal({ open, product, onClose, onSaved }: Props) {
  const [article, setArticle] = useState('')
  const [name, setName] = useState('')
  const [cost, setCost] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      setArticle(product?.product_article ?? '')
      setName(product?.product_name ?? '')
      setCost(product?.product_cost_usd ?? '')
      setError('')
    }
  }, [open, product])

  const submit = async () => {
    setError('')
    setBusy(true)
    const body = {
      product_article: article.trim(),
      product_name: name.trim(),
      product_cost_usd: (Number(cost.replace(',', '.')) || 0).toFixed(2),
    }
    try {
      if (product) await updateProduct(product.product_id, body)
      else await createProduct(body)
      onSaved()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить товар')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title={product ? 'Редактировать товар' : 'Новый товар'}
      onClose={onClose}
      width={420}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button
            variant="primary"
            loading={busy}
            disabled={!article.trim() || !name.trim()}
            onClick={submit}
          >
            Сохранить
          </Button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Артикул">
          <TextInput value={article} onChange={(e) => setArticle(e.target.value)} autoFocus />
        </Field>
        <Field label="Наименование">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Цена (USD)">
          <TextInput
            inputMode="decimal"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            placeholder="0.00"
          />
        </Field>
        {error && <div style={{ color: 'var(--danger)', fontSize: 13.5 }}>{error}</div>}
      </div>
    </Modal>
  )
}
