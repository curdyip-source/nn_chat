import type { AuditEvent } from '../../api/types'

// Человекочитаемые описания событий аудита.

const EVENT_LABELS: Record<string, string> = {
  'auth.login.succeeded': 'Вошёл в систему',
  'auth.login.failed': 'Неудачная попытка входа',
  'auth.login.inactive_user': 'Вход заблокирован — не подтверждён',
  'auth.refresh.succeeded': 'Продлил сессию',
  'auth.refresh.failed': 'Не удалось продлить сессию',
  'auth.refresh.inactive_user': 'Сессия отклонена — не подтверждён',
  'auth.logout.current': 'Вышел из системы',
  'auth.logout.all': 'Вышел со всех устройств',

  'user.bootstrap': 'Создан первый администратор',
  'user.register': 'Зарегистрировался',
  'user.create': 'Создал пользователя',
  'user.update': 'Изменил пользователя',
  'user.delete': 'Удалил пользователя',

  'document.create': 'Загрузил документ',
  'document.update': 'Изменил документ',

  'message.create': 'Отправил сообщение',
  'message.update': 'Изменил сообщение',
  'message.delete': 'Удалил сообщение',

  'order.create': 'Создал заказ',
  'order.update': 'Изменил заказ',
  'order.comment.create': 'Прокомментировал заказ',
  'order.comment.update': 'Изменил комментарий',
  'order.comment.delete': 'Удалил комментарий',

  'cdek.waybill.create': 'Создал накладную СДЭК',

  'inventory.create': 'Создал инвентаризацию',
  'inventory.update': 'Изменил инвентаризацию',

  'product_registration.create': 'Создал приёмку',
  'product_registration.update': 'Изменил приёмку',

  'product.create': 'Добавил товар',
  'product.update': 'Изменил товар',
  'product.delete': 'Удалил товар',

  'push.delivery_failed': 'Пуш не доставлен',
  'push.dispatch_failed': 'Ошибка отправки пуша',
  'push.mention_dispatch_failed': 'Ошибка пуша об упоминании',
  'push.order_change_dispatch_failed': 'Ошибка пуша об изменении заказа',
  'request.failed': 'Ошибка запроса',
  'application.startup.failed': 'Сбой запуска приложения',
}

// Иконка по группе события (префикс до точки).
const GROUP_ICONS: Record<string, string> = {
  auth: '🔑',
  user: '👤',
  order: '📦',
  product: '🏷️',
  product_registration: '📥',
  inventory: '📊',
  document: '📄',
  message: '💬',
  push: '🔔',
  request: '⚠️',
  application: '⚙️',
  cdek: '🚚',
}

// Существительное-цель по типу сущности (для строки «Заказ №5»).
const ENTITY_NOUNS: Record<string, string> = {
  order: 'Заказ',
  product: 'Товар',
  user: 'Пользователь',
  document: 'Документ',
  inventory: 'Инвентаризация',
  product_registration: 'Приёмка',
  message: 'Сообщение',
  session: 'Сессия',
  cdek: 'Заказ',
}

export type AuditView = {
  icon: string
  title: string
  target: string
  isError: boolean
}

export function describeAuditEvent(ev: AuditEvent): AuditView {
  const group = ev.event_type.split('.')[0]
  const title = EVENT_LABELS[ev.event_type] ?? ev.event_type
  const noun = ENTITY_NOUNS[ev.entity_type]
  const target = noun && ev.entity_id ? `${noun} №${ev.entity_id}` : noun ?? ''
  const isError = /fail|error/.test(ev.event_type)
  return { icon: GROUP_ICONS[group] ?? '•', title, target, isError }
}

// ----- Детализация изменения заказа (order.update) -----

const ORDER_FIELD_LABELS: Record<string, string> = {
  order_customer: 'клиент',
  order_status: 'статус заказа',
  order_establishment_name: 'склад',
  order_method_name: 'способ',
  order_sub_method: 'подспособ',
  order_contact_method: 'связь',
  order_sales_channel: 'канал продаж',
  order_info: 'информация',
}

const ITEM_FIELD_LABELS: Record<string, string> = {
  order_item_name: 'наименование',
  order_item_article: 'артикул',
  order_item_quantity: 'кол-во',
  order_item_price: 'цена',
  order_item_status: 'статус',
  order_item_note: 'заметка',
  order_item_source_establishment_name: 'откуда',
  order_item_destination_establishment_name: 'куда',
}

function fmtVal(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  return String(v)
}

type Change = { from?: unknown; to?: unknown }

export function describeOrderUpdate(payload: Record<string, unknown> | null): string[] {
  if (!payload) return []
  const lines: string[] = []
  const cf = (payload.changed_fields ?? {}) as Record<string, Change>
  for (const [field, label] of Object.entries(ORDER_FIELD_LABELS)) {
    const ch = cf[field]
    if (ch) lines.push(`${label}: «${fmtVal(ch.from)}» → «${fmtVal(ch.to)}»`)
  }
  const items = (payload.items ?? {}) as {
    added?: { after?: Record<string, unknown> }[]
    removed?: { before?: Record<string, unknown> }[]
    updated?: { changes?: Record<string, Change>; after?: Record<string, unknown>; before?: Record<string, unknown> }[]
  }
  for (const a of items.added ?? []) lines.push(`➕ добавлен товар «${fmtVal(a.after?.order_item_name)}»`)
  for (const r of items.removed ?? []) lines.push(`➖ убран товар «${fmtVal(r.before?.order_item_name)}»`)
  for (const u of items.updated ?? []) {
    const name = fmtVal(u.after?.order_item_name ?? u.before?.order_item_name)
    const parts: string[] = []
    for (const [field, label] of Object.entries(ITEM_FIELD_LABELS)) {
      const ch = u.changes?.[field]
      if (ch) parts.push(`${label} ${fmtVal(ch.from)}→${fmtVal(ch.to)}`)
    }
    if (parts.length) lines.push(`«${name}»: ${parts.join(', ')}`)
  }
  return lines
}

// ----- Детализация создания накладной СДЭК (cdek.waybill.create) -----

export function describeCdekWaybill(payload: Record<string, unknown> | null): string[] {
  if (!payload) return []
  const lines: string[] = []
  const track = payload.cdek_track_number
  lines.push(track ? `Накладная №${fmtVal(track)}` : 'Накладная (номер ещё не присвоен)')
  if (payload.city_name) lines.push(`Город: ${fmtVal(payload.city_name)}`)
  if (payload.recipient_name) lines.push(`Получатель: ${fmtVal(payload.recipient_name)}`)
  return lines
}

// Быстрые фильтры по типу сущности.
export const AUDIT_QUICK_FILTERS: { label: string; entityType: string | null }[] = [
  { label: 'Все', entityType: null },
  { label: 'Вход', entityType: 'session' },
  { label: 'Заказы', entityType: 'order' },
  { label: 'СДЭК', entityType: 'cdek' },
  { label: 'Товары', entityType: 'product' },
  { label: 'Пользователи', entityType: 'user' },
  { label: 'Сообщения', entityType: 'message' },
]
