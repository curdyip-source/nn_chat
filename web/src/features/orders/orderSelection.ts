import { createContext, useContext } from 'react'
import type { ItemExtra } from './itemStatusExtra'

/** Применить статус (+доп. поля перемещения/поставщика) к позициям заказа по их uid. */
export type BulkApplyFn = (uids: string[], statusId: number, extra: ItemExtra) => void
/** Удалить позиции заказа по их uid. */
export type BulkRemoveFn = (uids: string[]) => void
/** Данные позиции для копирования. */
export type BulkItemInfo = { name: string; quantity: number; price: string; sign: string }
/** Вернуть данные выбранных позиций заказа по их uid (для копирования). */
export type BulkCollectFn = (uids: string[]) => BulkItemInfo[]

export type OrderSelection = {
  isSelected: (orderId: number, uid: string) => boolean
  toggle: (orderId: number, uid: string) => void
  /** Каждая строка-заказ регистрирует функции массового применения/удаления для своих позиций. */
  registerApply: (orderId: number, fn: BulkApplyFn) => void
  unregisterApply: (orderId: number) => void
  registerRemove: (orderId: number, fn: BulkRemoveFn) => void
  unregisterRemove: (orderId: number) => void
  registerCollect: (orderId: number, fn: BulkCollectFn) => void
  unregisterCollect: (orderId: number) => void
  /** Выбор целых заказов (чекбоксы у свёрнутых строк) — для массовой смены статуса заказа. */
  isOrderSelected: (orderId: number) => boolean
  toggleOrder: (orderId: number) => void
}

const noop: OrderSelection = {
  isSelected: () => false,
  toggle: () => {},
  registerApply: () => {},
  unregisterApply: () => {},
  registerRemove: () => {},
  unregisterRemove: () => {},
  registerCollect: () => {},
  unregisterCollect: () => {},
  isOrderSelected: () => false,
  toggleOrder: () => {},
}

export const OrderSelectionContext = createContext<OrderSelection>(noop)
export const useOrderSelection = () => useContext(OrderSelectionContext)
