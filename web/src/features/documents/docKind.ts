import {
  createInventory,
  createRegistration,
  getInventory,
  getRegistration,
  listInventories,
  listRegistrations,
  updateInventoryStatus,
  updateRegistrationStatus,
} from '../../api/endpoints'
import type { Inventory, ProductRegistration } from '../../api/types'
import type { CartItem } from '../orders/cart'

// Общий вид документа (инвентаризация/приёмка нормализуются в него).
export type DocItemView = {
  id: number
  name: string
  article: string | null
  quantity: number
  cost: string
  currencyId: number | null
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
  items: DocItemView[]
}

export type ComposerState = {
  establishmentId: number
  supplier: string | null
  saveContact: boolean
  items: CartItem[]
}

export type DocKind = {
  key: 'inventory' | 'registration'
  title: string
  singular: string
  createTitle: string
  supplierLabel: string
  supplierRequired: boolean
  statusType: string
  list: (page: number, pageSize: number) => Promise<{ items: DocView[]; total: number }>
  get: (id: number) => Promise<DocView>
  create: (state: ComposerState) => Promise<void>
  updateStatus: (id: number, statusId: number) => Promise<DocView>
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
    items: r.items.map((it) => ({
      id: it.product_registration_item_id,
      name: it.product_registration_item_name,
      article: it.product_registration_item_article,
      quantity: it.product_registration_item_quantity,
      cost: it.product_registration_item_cost,
      currencyId: it.product_registration_item_currency_id ?? null,
    })),
  }
}

function itemBody(it: CartItem, prefix: string) {
  return {
    product_id: it.productId,
    product_article: it.productId ? null : it.article,
    product_name: it.productId ? null : it.name,
    [`${prefix}_quantity`]: it.quantity,
    [`${prefix}_cost`]: (Number(it.price) || 0).toFixed(2),
    [`${prefix}_currency_id`]: it.currencyId,
  }
}

export const INVENTORY_KIND: DocKind = {
  key: 'inventory',
  title: 'Инвентаризации',
  singular: 'Инвентаризация',
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
  updateStatus: (id, statusId) => updateInventoryStatus(id, statusId).then((r) => normInventory(r.item)),
}

export const REGISTRATION_KIND: DocKind = {
  key: 'registration',
  title: 'Приёмки',
  singular: 'Приёмка',
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
      items: s.items.map((it) => itemBody(it, 'product_registration_item')),
    }).then(() => undefined),
  updateStatus: (id, statusId) =>
    updateRegistrationStatus(id, statusId).then((r) => normRegistration(r.item)),
}
