import {
  createInventory,
  createRegistration,
  deleteInventory,
  deleteRegistration,
  getInventory,
  getRegistration,
  listInventories,
  listRegistrations,
  updateInventory,
  updateInventoryStatus,
  updateRegistration,
  updateRegistrationStatus,
} from '../../api/endpoints'
import type { Inventory, ProductRegistration } from '../../api/types'
import type { CartItem } from '../orders/cart'

// Общий вид документа (инвентаризация/приёмка нормализуются в него).
export type DocItemView = {
  id: number
  productId: number | null
  name: string
  article: string | null
  quantity: number
  cost: string
  currencyId: number | null
  /** Только приёмка: вес штуки и доставка по весу (считает сервер). */
  weight?: string | null
  shippingPerUnit?: string | null
  costPerUnit?: string | null
  lineTotal?: string | null
}

export type DocView = {
  id: number
  supplier: string | null
  establishmentId: number | null
  establishmentName: string | null
  statusId: number | null
  status: string | null
  statusColor: string | null
  createdAt: string | null
  /** Только приёмка: доставка всей партии. */
  shippingCost?: string | null
  shippingCurrencyId?: number | null
  items: DocItemView[]
}

export type ComposerState = {
  establishmentId: number
  supplier: string | null
  saveContact: boolean
  /** Только приёмка; null — доставки нет. */
  shippingCost?: string | null
  shippingCurrencyId?: number | null
  items: CartItem[]
}

export type DocKind = {
  key: 'inventory' | 'registration'
  title: string
  singular: string
  /** Винительный падеж для «Удалить …»: инвентаризацию / приёмку. */
  accusative: string
  createTitle: string
  supplierLabel: string
  supplierRequired: boolean
  statusType: string
  list: (page: number, pageSize: number) => Promise<{ items: DocView[]; total: number }>
  get: (id: number) => Promise<DocView>
  create: (state: ComposerState) => Promise<void>
  update: (id: number, state: ComposerState) => Promise<void>
  updateStatus: (id: number, statusId: number) => Promise<DocView>
  remove: (id: number) => Promise<void>
}

function normInventory(r: Inventory): DocView {
  return {
    id: r.inventory_id,
    supplier: r.inventory_supplier ?? null,
    establishmentId: r.inventory_establishment_id ?? null,
    establishmentName: r.inventory_establishment_name ?? null,
    statusId: r.inventory_status_id ?? null,
    status: r.inventory_status ?? null,
    statusColor: r.inventory_status_color ?? null,
    createdAt: r.inventory_created_at ?? null,
    items: r.items.map((it) => ({
      id: it.inventory_item_id,
      productId: it.inventory_item_product_id ?? null,
      name: it.inventory_item_name,
      article: it.inventory_item_article,
      quantity: it.inventory_item_quantity,
      cost: it.inventory_item_cost,
      currencyId: it.inventory_item_currency_id ?? null,
    })),
  }
}

function normRegistration(r: ProductRegistration): DocView {
  return {
    id: r.product_registration_id,
    supplier: r.product_registration_supplier ?? null,
    establishmentId: r.product_registration_establishment_id ?? null,
    establishmentName: r.product_registration_establishment_name ?? null,
    statusId: r.product_registration_status_id ?? null,
    status: r.product_registration_status ?? null,
    statusColor: r.product_registration_status_color ?? null,
    createdAt: r.product_registration_created_at ?? null,
    shippingCost: r.product_registration_shipping_cost ?? null,
    shippingCurrencyId: r.product_registration_shipping_currency_id ?? null,
    items: r.items.map((it) => ({
      id: it.product_registration_item_id,
      productId: it.product_registration_item_product_id ?? null,
      name: it.product_registration_item_name,
      article: it.product_registration_item_article,
      quantity: it.product_registration_item_quantity,
      cost: it.product_registration_item_cost,
      currencyId: it.product_registration_item_currency_id ?? null,
      weight: it.product_registration_item_weight ?? null,
      shippingPerUnit: it.product_registration_item_shipping_per_unit ?? null,
      costPerUnit: it.product_registration_item_cost_per_unit ?? null,
      lineTotal: it.product_registration_item_line_total ?? null,
    })),
  }
}

function itemBody(it: CartItem, prefix: string) {
  return {
    product_id: it.productId,
    // Снимок (артикул+название) шлём ВСЕГДА — чтобы бэкенд восстановил позицию, даже
    // если товар удалён/пересобран при федерации каталога (иначе «Товар не найден»).
    product_article: it.article,
    product_name: it.name,
    [`${prefix}_quantity`]: it.quantity,
    [`${prefix}_cost`]: (Number(it.price) || 0).toFixed(2),
    [`${prefix}_currency_id`]: it.currencyId,
  }
}

/** Вес из поля в формате API (до 3 знаков); пусто, ноль или мусор — null. */
export function apiWeight(raw: string | null | undefined): string | null {
  const value = Number((raw ?? '').replace(',', '.'))
  return Number.isFinite(value) && value >= 0.001 ? value.toFixed(3) : null
}

// Вес и доставку шлём всегда, null в том числе: ключа нет — сервер оставил бы прежние.
function registrationItemBody(it: CartItem) {
  return { ...itemBody(it, 'product_registration_item'), product_registration_item_weight: apiWeight(it.weight) }
}

function registrationShippingBody(s: ComposerState) {
  return {
    product_registration_shipping_cost: s.shippingCost ?? null,
    product_registration_shipping_currency_id: s.shippingCost ? (s.shippingCurrencyId ?? null) : null,
  }
}

export const INVENTORY_KIND: DocKind = {
  key: 'inventory',
  title: 'Инвентаризации',
  singular: 'Инвентаризация',
  accusative: 'инвентаризацию',
  createTitle: 'Новая инвентаризация',
  supplierLabel: 'Поставщик',
  supplierRequired: false,
  statusType: 'inventory',
  list: (page, pageSize) =>
    listInventories({ page, pageSize }).then((r) => ({
      items: r.items.map(normInventory),
      total: r.pagination?.total ?? r.items.length,
    })),
  get: (id) => getInventory(id).then((r) => normInventory(r.item)),
  create: (s) =>
    createInventory({
      inventory_establishment_id: s.establishmentId,
      inventory_supplier: s.supplier,
      save_contact: s.saveContact,
      items: s.items.map((it) => itemBody(it, 'inventory_item')),
    }).then(() => undefined),
  update: (id, s) =>
    updateInventory(id, {
      inventory_establishment_id: s.establishmentId,
      inventory_supplier: s.supplier,
      items: s.items.map((it) => itemBody(it, 'inventory_item')),
    }).then(() => undefined),
  updateStatus: (id, statusId) => updateInventoryStatus(id, statusId).then((r) => normInventory(r.item)),
  remove: (id) => deleteInventory(id),
}

export const REGISTRATION_KIND: DocKind = {
  key: 'registration',
  title: 'Приёмки',
  singular: 'Приёмка',
  accusative: 'приёмку',
  createTitle: 'Новая приёмка',
  supplierLabel: 'Поставщик',
  supplierRequired: true,
  statusType: 'product_registration',
  list: (page, pageSize) =>
    listRegistrations({ page, pageSize }).then((r) => ({
      items: r.items.map(normRegistration),
      total: r.pagination?.total ?? r.items.length,
    })),
  get: (id) => getRegistration(id).then((r) => normRegistration(r.item)),
  create: (s) =>
    createRegistration({
      product_registration_establishment_id: s.establishmentId,
      product_registration_supplier: s.supplier,
      save_contact: s.saveContact,
      ...registrationShippingBody(s),
      items: s.items.map(registrationItemBody),
    }).then(() => undefined),
  update: (id, s) =>
    updateRegistration(id, {
      product_registration_establishment_id: s.establishmentId,
      product_registration_supplier: s.supplier,
      ...registrationShippingBody(s),
      items: s.items.map(registrationItemBody),
    }).then(() => undefined),
  updateStatus: (id, statusId) =>
    updateRegistrationStatus(id, statusId).then((r) => normRegistration(r.item)),
  remove: (id) => deleteRegistration(id),
}
