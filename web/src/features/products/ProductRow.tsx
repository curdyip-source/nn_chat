import { useState } from 'react'
import { deleteProduct, updateProduct } from '../../api/endpoints'
import type { Product } from '../../api/types'
import styles from './ProductsPage.module.css'

type Props = {
  product: Product
  /** Колонка «Кем создан» — для созданных пользователями. */
  showOwner?: boolean
  onChanged: () => void
  onError: (msg: string) => void
}

export function ProductRow({ product, showOwner = false, onChanged, onError }: Props) {
  const [article, setArticle] = useState(product.product_article)
  const [name, setName] = useState(product.product_name)
  const [cost, setCost] = useState(product.product_cost_usd)
  const weightText = (raw: string | null | undefined) => (raw ? String(Number(raw)) : '')
  const [weight, setWeight] = useState(weightText(product.product_weight))
  // Последний сохранённый вес: строка товара после сохранения не перечитывается.
  const [savedWeight, setSavedWeight] = useState(weightText(product.product_weight))
  const [saving, setSaving] = useState(false)

  const save = async (patch: { product_article?: string; product_name?: string; product_cost_usd?: string; product_weight?: string | null }) => {
    setSaving(true)
    try {
      await updateProduct(product.product_id, patch)
      onError('')
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Не удалось сохранить')
      // откат к исходным значениям
      setArticle(product.product_article)
      setName(product.product_name)
      setCost(product.product_cost_usd)
    } finally {
      setSaving(false)
    }
  }

  const saveArticle = () => {
    const v = article.trim()
    if (!v || v === product.product_article) {
      setArticle(product.product_article)
      return
    }
    void save({ product_article: v })
  }
  const saveName = () => {
    const v = name.trim()
    if (!v || v === product.product_name) {
      setName(product.product_name)
      return
    }
    void save({ product_name: v })
  }
  const saveCost = () => {
    const v = (Number(cost.replace(',', '.')) || 0).toFixed(2)
    if (v === product.product_cost_usd) {
      setCost(product.product_cost_usd)
      return
    }
    void save({ product_cost_usd: v })
  }

  // Вес — в справочник по наименованию: перезаписывает прежний, пустое поле стирает.
  const saveWeight = async () => {
    const value = Number(weight.replace(',', '.'))
    const cleared = !weight.trim()
    if (!cleared && (!Number.isFinite(value) || value < 0.001)) {
      setWeight(savedWeight)
      return
    }
    const next = cleared ? '' : String(Number(value.toFixed(3)))
    setWeight(next)
    if (next === savedWeight) return
    setSaving(true)
    try {
      await updateProduct(product.product_id, { product_weight: cleared ? null : value.toFixed(3) })
      setSavedWeight(next)
      onError('')
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Не удалось сохранить вес')
      setWeight(savedWeight)
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    if (!window.confirm(`Удалить товар «${product.product_name}»?`)) return
    setSaving(true)
    try {
      await deleteProduct(product.product_id)
      onChanged()
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Не удалось удалить')
      setSaving(false)
    }
  }

  return (
    <div className={[styles.row, showOwner ? styles.rowWithOwner : '', saving ? styles.saving : ''].join(' ')}>
      <input className={styles.cellInput} value={article} onChange={(e) => setArticle(e.target.value)} onBlur={saveArticle} />
      <input className={styles.cellInput} value={name} onChange={(e) => setName(e.target.value)} onBlur={saveName} />
      {showOwner && (
        <span className={styles.owner} title={product.product_created_at ?? undefined}>
          {product.product_owner_user_login ?? '—'}
        </span>
      )}
      <input
        className={[styles.cellInput, styles.rightInput].join(' ')}
        inputMode="decimal"
        placeholder="—"
        value={weight}
        onChange={(e) => setWeight(e.target.value)}
        onBlur={saveWeight}
      />
      <input
        className={[styles.cellInput, styles.rightInput].join(' ')}
        inputMode="decimal"
        value={cost}
        onChange={(e) => setCost(e.target.value)}
        onBlur={saveCost}
      />
      <button className={styles.delBtn} onClick={remove} title="Удалить">
        ✕
      </button>
    </div>
  )
}
