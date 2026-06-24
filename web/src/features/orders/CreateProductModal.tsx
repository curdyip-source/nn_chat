import { useEffect, useState } from 'react'
import { createProduct } from '../../api/endpoints'
import type { Product } from '../../api/types'
import { Button } from '../../ui/Button'
import { Field, TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'

type Props = {
  open: boolean
  defaultName: string
  onClose: () => void
  onCreated: (product: Product) => void
}

export function CreateProductModal({ open, defaultName, onClose, onCreated }: Props) {
  const [article, setArticle] = useState('')
  const [name, setName] = useState(defaultName)
  const [cost, setCost] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      setName(defaultName)
      setArticle('')
      setCost('')
      setError('')
    }
  }, [open, defaultName])

  const submit = async () => {
    setError('')
    setBusy(true)
    try {
      const { item } = await createProduct({
        product_article: article.trim(),
        product_name: name.trim(),
        product_cost_usd: (Number(cost.replace(',', '.')) || 0).toFixed(2),
      })
      onCreated(item)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось создать товар')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title="Новый товар"
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
            Создать и добавить
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
