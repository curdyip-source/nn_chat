import { useEffect, useState } from 'react'
import { createProduct } from '../../api/endpoints'
import type { Product } from '../../api/types'
import { Button } from '../../ui/Button'
import { Field, TextInput } from '../../ui/Field'
import { Modal } from '../../ui/Modal'
import styles from './CreateMissingProductsModal.module.css'

type Props = {
  open: boolean
  /** Ненайденные названия из вставленного списка — по одному на страницу. */
  names: string[]
  /** Вызывается после создания товара для строки name (чтобы добавить его в корзину). */
  onCreated: (name: string, product: Product) => void
  onClose: () => void
  /** Цены из вставленного списка по наименованию — префилл поля «Цена». */
  prices?: Record<string, string>
}

type Mark = 'created' | 'skipped' | undefined

export function CreateMissingProductsModal({ open, names, onCreated, onClose, prices }: Props) {
  const [index, setIndex] = useState(0)
  const [article, setArticle] = useState('')
  const [name, setName] = useState('')
  const [cost, setCost] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [marks, setMarks] = useState<Mark[]>([])
  // Снимок списка на момент открытия: родитель убирает созданные из missingNames,
  // поэтому итерируемся по зафиксированной копии, чтобы индексы страниц не «поехали».
  const [list, setList] = useState<string[]>([])

  // Сброс мастера и фиксация списка при открытии.
  useEffect(() => {
    if (open) {
      setIndex(0)
      setMarks([])
      setList(names)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  // На каждой странице подставляем название из списка как наименование.
  useEffect(() => {
    const lineName = list[index] ?? ''
    setName(lineName)
    setArticle('')
    setCost(prices?.[lineName] ?? '')
    setError('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, list])

  const total = list.length
  const current = list[index] ?? ''
  const last = index >= total - 1

  const mark = (value: Mark) =>
    setMarks((prev) => {
      const next = [...prev]
      next[index] = value
      return next
    })

  const advance = () => {
    if (last) onClose()
    else setIndex((i) => i + 1)
  }

  const skip = () => {
    mark('skipped')
    advance()
  }

  const submit = async () => {
    setError('')
    setBusy(true)
    try {
      const { item } = await createProduct({
        product_article: article.trim(),
        product_name: name.trim(),
        product_cost_usd: (Number(cost.replace(',', '.')) || 0).toFixed(2),
      })
      onCreated(current, item)
      mark('created')
      advance()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось создать товар')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title={`Новый товар · ${index + 1} из ${total}`}
      onClose={onClose}
      width={460}
      footer={
        <>
          <Button variant="ghost" onClick={skip}>
            {last ? 'Пропустить и закрыть' : 'Пропустить'}
          </Button>
          <Button
            variant="primary"
            loading={busy}
            disabled={!name.trim()}
            onClick={submit}
          >
            {last ? 'Создать и завершить' : 'Создать и далее'}
          </Button>
        </>
      }
    >
      <div className={styles.body}>
        <div className={styles.dots}>
          {list.map((n, i) => (
            <span
              key={i}
              title={n}
              className={[
                styles.dot,
                i === index ? styles.dotActive : '',
                marks[i] === 'created' ? styles.dotDone : '',
                marks[i] === 'skipped' ? styles.dotSkip : '',
              ].join(' ')}
            >
              {i + 1}
            </span>
          ))}
        </div>

        <div className={styles.srcLine}>
          Из списка: <b>{current}</b>
        </div>

        <Field label="Наименование">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </Field>
        <Field label="Артикул (необязательно)">
          <TextInput
            value={article}
            onChange={(e) => setArticle(e.target.value)}
            placeholder="авто, если пусто"
          />
        </Field>
        <Field label="Цена (USD)">
          <TextInput
            inputMode="decimal"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            placeholder="0.00"
          />
        </Field>
        {error && <div className={styles.error}>{error}</div>}
      </div>
    </Modal>
  )
}
