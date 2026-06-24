// Спец-статусы позиции заказа, требующие доп. данных (как в приложении).
export const MOVEMENT_STATUS = 'Перемещение'
export const SUPPLIER_STATUS = 'Заказ поставщику'

export type ExtraMode = 'movement' | 'supplier'

export function statusExtraMode(statusName: string | undefined | null): ExtraMode | null {
  if (statusName === MOVEMENT_STATUS) return 'movement'
  if (statusName === SUPPLIER_STATUS) return 'supplier'
  return null
}

export type ItemExtra = {
  supplier?: string | null
  sourceEstablishmentId?: number | null
  destinationEstablishmentId?: number | null
}
