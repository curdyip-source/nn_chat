// Спец-статусы позиции заказа, требующие доп. данных (как в приложении).
export const MOVEMENT_STATUS = 'Перемещение'
export const SUPPLIER_STATUS = 'Заказ поставщику'
// «Заказано» наследует поставщика от «Заказ поставщику» — отдельного ввода не требует,
// но поставщика показывает (и хранит) так же.
export const ORDERED_STATUS = 'Заказано'

export type ExtraMode = 'movement' | 'supplier'

export function statusExtraMode(statusName: string | undefined | null): ExtraMode | null {
  if (statusName === MOVEMENT_STATUS) return 'movement'
  if (statusName === SUPPLIER_STATUS) return 'supplier'
  return null
}

/** Статус показывает маршрут перемещения (склад → склад). */
export function showsMovement(statusName: string | undefined | null): boolean {
  return statusName === MOVEMENT_STATUS
}

/** Статус показывает поставщика (Заказ поставщику и унаследовавший его Заказано). */
export function showsSupplier(statusName: string | undefined | null): boolean {
  return statusName === SUPPLIER_STATUS || statusName === ORDERED_STATUS
}

export type ItemExtra = {
  supplier?: string | null
  sourceEstablishmentId?: number | null
  destinationEstablishmentId?: number | null
}
