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

// Быстрые фильтры по типу сущности.
export const AUDIT_QUICK_FILTERS: { label: string; entityType: string | null }[] = [
  { label: 'Все', entityType: null },
  { label: 'Вход', entityType: 'session' },
  { label: 'Заказы', entityType: 'order' },
  { label: 'Товары', entityType: 'product' },
  { label: 'Пользователи', entityType: 'user' },
  { label: 'Сообщения', entityType: 'message' },
]
