import type { Order, OrderUpdate, OrderUpdateItem } from '../../api/types'

function defaultItems(order: Order): OrderUpdateItem[] {
  return order.items.map((it) => ({
    product_id: it.order_item_product_id ?? null,
    product_article: it.order_item_product_id ? null : it.order_item_article,
    product_name: it.order_item_product_id ? null : it.order_item_name,
    order_item_quantity: it.order_item_quantity,
    order_item_price: it.order_item_price,
    order_item_status_id: it.order_item_status_id ?? null,
    order_item_currency_id: it.order_item_currency_id ?? null,
    order_item_supplier: it.order_item_supplier ?? null,
    order_item_note: it.order_item_note ?? null,
  }))
}

/** Собирает payload PUT /orders из заказа с точечными правками. */
export function orderToUpdate(
  order: Order,
  overrides: { customer?: string; statusId?: number; items?: OrderUpdateItem[] } = {},
): OrderUpdate {
  return {
    order_establishment_id: order.order_establishment_id!,
    order_method_id: order.order_method_id!,
    order_sub_method: order.order_sub_method ?? null,
    order_contact_method: order.order_contact_method ?? null,
    order_customer: overrides.customer ?? order.order_customer,
    order_info: order.order_info,
    order_status_id: overrides.statusId ?? order.order_status_id!,
    items: overrides.items ?? defaultItems(order),
  }
}
