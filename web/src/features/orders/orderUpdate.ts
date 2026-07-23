import type { Order, OrderUpdate, OrderUpdateItem } from '../../api/types'

function defaultItems(order: Order): OrderUpdateItem[] {
  return order.items.map((it) => ({
    product_id: it.order_item_product_id ?? null,
    // Снимок (артикул+название) шлём ВСЕГДА — чтобы бэкенд восстановил позицию, даже
    // если товар удалён/пересобран при федерации каталога (иначе «Товар не найден»).
    product_article: it.order_item_article,
    product_name: it.order_item_name,
    order_item_quantity: it.order_item_quantity,
    order_item_price: it.order_item_price,
    order_item_status_id: it.order_item_status_id ?? null,
    order_item_currency_id: it.order_item_currency_id ?? null,
    order_item_supplier: it.order_item_supplier ?? null,
    order_item_note: it.order_item_note ?? null,
    order_item_source_establishment_id: it.order_item_source_establishment_id ?? null,
    order_item_destination_establishment_id: it.order_item_destination_establishment_id ?? null,
  }))
}

/** Payload PUT /orders для «отмены заказа с товарами»: статус заказа = отменённый,
 *  всем позициям — статус товара «Отменен». */
export function orderToCancelAll(
  order: Order,
  cancelledOrderStatusId: number,
  cancelledItemStatusId: number,
): OrderUpdate {
  return orderToUpdate(order, {
    statusId: cancelledOrderStatusId,
    items: order.items.map((it) => ({
      product_id: it.order_item_product_id ?? null,
      product_article: it.order_item_article,
      product_name: it.order_item_name,
      order_item_quantity: it.order_item_quantity,
      order_item_price: it.order_item_price,
      order_item_status_id: cancelledItemStatusId,
      order_item_currency_id: it.order_item_currency_id ?? null,
      order_item_supplier: it.order_item_supplier ?? null,
      order_item_note: it.order_item_note ?? null,
      order_item_source_establishment_id: it.order_item_source_establishment_id ?? null,
      order_item_destination_establishment_id: it.order_item_destination_establishment_id ?? null,
    })),
  })
}

/** Payload PUT /orders для перевода в «На сборку», когда все товары готовы
 *  (нет ожидаемых): статус заказа = «На сборку», «Не будет» → «Отменен». */
export function orderToAssembly(
  order: Order,
  assemblyStatusId: number,
  cancelledItemStatusId: number | null,
): OrderUpdate {
  return orderToUpdate(order, {
    statusId: assemblyStatusId,
    items: order.items.map((it) => ({
      product_id: it.order_item_product_id ?? null,
      product_article: it.order_item_article,
      product_name: it.order_item_name,
      order_item_quantity: it.order_item_quantity,
      order_item_price: it.order_item_price,
      order_item_status_id:
        it.order_item_status === 'Не будет' && cancelledItemStatusId != null
          ? cancelledItemStatusId
          : it.order_item_status_id ?? null,
      order_item_currency_id: it.order_item_currency_id ?? null,
      order_item_supplier: it.order_item_supplier ?? null,
      order_item_note: it.order_item_note ?? null,
      order_item_source_establishment_id: it.order_item_source_establishment_id ?? null,
      order_item_destination_establishment_id: it.order_item_destination_establishment_id ?? null,
    })),
  })
}

/** Собирает payload PUT /orders из заказа с точечными правками. */
export function orderToUpdate(
  order: Order,
  overrides: { customer?: string; info?: string; statusId?: number; items?: OrderUpdateItem[] } = {},
): OrderUpdate {
  return {
    order_establishment_id: order.order_establishment_id!,
    order_method_id: order.order_method_id!,
    order_sub_method: order.order_sub_method ?? null,
    order_contact_method: order.order_contact_method ?? null,
    order_sales_channel: order.order_sales_channel ?? null,
    order_customer: overrides.customer ?? order.order_customer,
    order_info: overrides.info ?? order.order_info,
    order_status_id: overrides.statusId ?? order.order_status_id!,
    items: overrides.items ?? defaultItems(order),
  }
}
