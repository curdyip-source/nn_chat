import { useState } from 'react'
import { matchProductsByName } from '../../api/endpoints'
import type { Currency, Product } from '../../api/types'
import { parsePastedList, type PastedItem } from '../../lib/pastedList'
import { cartItemFromProduct, type CartItem } from './cart'
import { CreateMissingProductsModal } from './CreateMissingProductsModal'
import styles from './OrderCreate.module.css'

/** Подсказка под поиском товаров: какие списки можно вставить (Ctrl/⌘+V). */
export function PastedListHint() {
  return (
    <div className={styles.pasteHint}>
      Можно вставить список (Ctrl/⌘+V) — по строке на товар. Форматы:
      <code>1. Kajal: Dahab 100ml 1 x 8224₽ = 8224₽</code>
      <code>1 шт⇥Kajal: Dahab 100ml⇥64</code>
      <code>1 шт. * Kajal: Dahab 100ml * 8224 ₽</code>
      или просто наименования. Количество и цена берутся из строки, ₽ / $ / € — валюта.
    </div>
  )
}

/**
 * Вставка списка в поиск товаров — общая для заказа, приёмки и инвентаризации.
 * Строки разбираются тем же парсером, что в приложении, наименования сопоставляются
 * с номенклатурой; найденное уходит в корзину с количеством/ценой/валютой из строки,
 * для ненайденного — мастер «Создать ненайденные».
 */
export function usePastedListImport({
  currencies,
  defaultCurrencyId,
  addMany,
}: {
  currencies: Currency[]
  defaultCurrencyId: number | null
  addMany: (items: CartItem[]) => void
}) {
  const [note, setNote] = useState<string | null>(null)
  const [missingNames, setMissingNames] = useState<string[]>([])
  const [missingOpen, setMissingOpen] = useState(false)
  const [pastedByName, setPastedByName] = useState<Record<string, PastedItem>>({})

  const currencyIdFor = (code: string | null) =>
    (code && currencies.find((c) => c.currency_name.toUpperCase() === code)?.currency_id) || defaultCurrencyId

  const toCartItem = (product: Product, pasted: PastedItem | undefined): CartItem => {
    const base = cartItemFromProduct(product, defaultCurrencyId)
    if (!pasted) return base
    return {
      ...base,
      quantity: pasted.quantity,
      ...(pasted.price != null ? { price: pasted.price, currencyId: currencyIdFor(pasted.currencyCode) } : {}),
    }
  }

  const onBulkPaste = async (lines: string[]) => {
    const parsed = parsePastedList(lines.join('\n'))
    if (!parsed.length) {
      setNote('В списке не нашлось позиций')
      return
    }
    setNote(`Ищу ${parsed.length} поз. в номенклатуре…`)
    try {
      const { results } = await matchProductsByName(parsed.map((p) => p.name))
      const found: CartItem[] = []
      const missing: string[] = []
      const byName: Record<string, PastedItem> = {}
      results.forEach((r, i) => {
        byName[parsed[i].name] = parsed[i]
        if (r.matched) found.push(toCartItem(r.matched, parsed[i]))
        else missing.push(r.query)
      })
      if (found.length) addMany(found)
      setMissingNames(missing)
      setPastedByName(byName)
      const anyPrice = parsed.some((p) => p.price != null)
      setNote(
        `Добавлено ${found.length} из ${results.length}` +
          (anyPrice ? ', цены подтянуты' : '') +
          (missing.length ? ` · не найдено: ${missing.length}` : ''),
      )
    } catch {
      setMissingNames([])
      setNote('Не удалось распознать список')
    }
  }

  // Товар создан в мастере для строки name — кладём в корзину с данными из строки.
  const onMissingCreated = (name: string, product: Product) => {
    addMany([toCartItem(product, pastedByName[name])])
    setMissingNames((prev) => prev.filter((n) => n !== name))
  }

  const prices = Object.fromEntries(
    Object.entries(pastedByName)
      .filter(([, p]) => p.price != null)
      .map(([name, p]) => [name, p.price as string]),
  )

  const noteView = note && (
    <div className={styles.bulkNote}>
      <span>{note}</span>
      {missingNames.length > 0 && (
        <button type="button" className={styles.createLink} onClick={() => setMissingOpen(true)}>
          + Создать ненайденные ({missingNames.length})
        </button>
      )}
      <button type="button" className={styles.bulkClose} onClick={() => setNote(null)} aria-label="Скрыть">
        ✕
      </button>
    </div>
  )

  const modal = (
    <CreateMissingProductsModal
      open={missingOpen}
      names={missingNames}
      prices={prices}
      onCreated={onMissingCreated}
      onClose={() => setMissingOpen(false)}
    />
  )

  return { onBulkPaste, noteView, modal }
}
