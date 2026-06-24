import type { Product } from '../../api/types'

/** Локальная позиция корзины при сборке заказа. */
export type CartItem = {
  uid: string
  productId: number | null
  article: string | null
  name: string
  quantity: number
  price: string // строка для аккуратного ввода десятичных
  currencyId: number | null
  statusId?: number | null // статус позиции (для заказов; сохраняется при редактировании)
}

export function newUid(): string {
  return crypto.randomUUID()
}

export function cartItemFromProduct(product: Product, currencyId: number | null): CartItem {
  return {
    uid: newUid(),
    productId: product.product_id,
    article: product.product_article,
    name: product.product_name,
    quantity: 1,
    price: product.product_cost_usd ?? '',
    currencyId,
  }
}
