import { apiRequest } from './client'
import type {
  AuditEvent,
  AuthResponse,
  ChatMessage,
  Contact,
  Currency,
  Establishment,
  Inventory,
  Order,
  OrderCreate,
  OrderMethod,
  OrderUpdate,
  Paginated,
  Product,
  ProductImportJob,
  ProductRegistration,
  ReferenceData,
  SetupStatus,
  Status,
  User,
} from './types'

// ---------- Auth ----------

export function login(user_login: string, user_password: string) {
  return apiRequest<AuthResponse>('/auth/login', {
    method: 'POST',
    body: { user_login, user_password },
    silent401: true,
  })
}

export function fetchMe() {
  return apiRequest<{ user: User }>('/auth/me')
}

export function fetchSetupStatus() {
  return apiRequest<SetupStatus>('/setup-status')
}

export function logout() {
  return apiRequest('/auth/logout', { method: 'POST' }).catch(() => undefined)
}

// ---------- Reference data ----------

export function fetchReferenceData() {
  return apiRequest<ReferenceData>('/reference-data')
}

// Справочники: CRUD.
export function saveEstablishment(
  id: number | null,
  body: { establishment_name: string; establishment_address?: string | null },
) {
  return apiRequest<{ item: Establishment }>(
    id ? `/establishments/${id}` : '/establishments',
    { method: id ? 'PUT' : 'POST', body },
  )
}

export function saveOrderMethod(
  id: number | null,
  body: { order_method_name: string; order_method_sub_methods?: string[] },
) {
  return apiRequest<{ item: OrderMethod }>(
    id ? `/order-methods/${id}` : '/order-methods',
    { method: id ? 'PUT' : 'POST', body },
  )
}

export function saveStatus(
  id: number | null,
  body: { status_type: string; status_status: string; status_color?: string | null },
) {
  return apiRequest<{ item: Status }>(id ? `/statuses/${id}` : '/statuses', {
    method: id ? 'PUT' : 'POST',
    body,
  })
}

export function saveCurrency(
  id: number | null,
  body: { currency_name: string; currency_sign?: string | null },
) {
  return apiRequest<{ item: Currency }>(id ? `/currencies/${id}` : '/currencies', {
    method: id ? 'PUT' : 'POST',
    body,
  })
}

// ---------- Products ----------

export function searchProducts(search: string, signal?: AbortSignal) {
  const q = new URLSearchParams({ search, page: '1', page_size: '20' })
  return apiRequest<Paginated<Product>>(`/products?${q}`, { signal })
}

export function listProducts(opts: { search?: string; page?: number; pageSize?: number } = {}) {
  const q = new URLSearchParams({
    page: String(opts.page ?? 1),
    page_size: String(opts.pageSize ?? 50),
  })
  if (opts.search) q.set('search', opts.search)
  return apiRequest<Paginated<Product>>(`/products?${q}`)
}

export function createProduct(input: {
  product_article: string
  product_name: string
  product_cost_usd: string
}) {
  return apiRequest<{ item: Product }>('/products', { method: 'POST', body: input })
}

export function updateProduct(
  productId: number,
  patch: { product_article?: string; product_name?: string; product_cost_usd?: string },
) {
  return apiRequest<{ item: Product }>(`/products/${productId}`, { method: 'PUT', body: patch })
}

export function deleteProduct(productId: number) {
  return apiRequest<void>(`/products/${productId}`, { method: 'DELETE' })
}

export function importProductsXlsx(file: File) {
  const form = new FormData()
  form.append('file', file)
  return apiRequest<{ item: ProductImportJob }>('/products/import-xlsx', {
    method: 'POST',
    body: form,
  })
}

export function getProductImportJob(jobId: string) {
  return apiRequest<{ item: ProductImportJob }>(`/products/import-xlsx/${jobId}`)
}

/** Сопоставление списка наименований с номенклатурой (для Excel-импорта в заказ). */
export type ProductMatchRow = {
  query: string
  matched: Product | null
  candidates: Product[]
}

export function matchProductsByName(names: string[], signal?: AbortSignal) {
  return apiRequest<{ results: ProductMatchRow[] }>('/products/match', {
    method: 'POST',
    body: { names },
    signal,
  })
}

// ---------- Contacts ----------

export function searchContacts(
  contactType: 'buyer' | 'supplier',
  search: string,
  signal?: AbortSignal,
) {
  const q = new URLSearchParams({
    contact_type: contactType,
    search,
    page: '1',
    page_size: '20',
  })
  return apiRequest<Paginated<Contact>>(`/contacts?${q}`, { signal })
}

export function listContacts(
  contactType: 'buyer' | 'supplier',
  opts: { search?: string; page?: number; pageSize?: number } = {},
) {
  const q = new URLSearchParams({
    contact_type: contactType,
    page: String(opts.page ?? 1),
    page_size: String(opts.pageSize ?? 50),
  })
  if (opts.search) q.set('search', opts.search)
  return apiRequest<Paginated<Contact>>(`/contacts?${q}`)
}

// ---------- Orders ----------

export function listOrders(
  opts: { page?: number; pageSize?: number; statusIds?: number[]; methodIds?: number[]; search?: string } = {},
) {
  const q = new URLSearchParams({
    page: String(opts.page ?? 1),
    page_size: String(opts.pageSize ?? 30),
  })
  for (const id of opts.statusIds ?? []) q.append('status_id', String(id))
  for (const id of opts.methodIds ?? []) q.append('method_id', String(id))
  if (opts.search) q.set('search', opts.search)
  return apiRequest<Paginated<Order>>(`/orders?${q}`)
}

export function createOrder(payload: OrderCreate) {
  return apiRequest<{ item: Order }>('/orders', { method: 'POST', body: payload })
}

export function getOrder(orderId: number) {
  return apiRequest<{ item: Order }>(`/orders/${orderId}`)
}

export function updateOrderStatus(orderId: number, statusId: number) {
  return apiRequest<{ item: Order }>(`/orders/${orderId}/status`, {
    method: 'PUT',
    body: { order_status_id: statusId },
  })
}

export function updateOrder(orderId: number, payload: OrderUpdate) {
  return apiRequest<{ item: Order }>(`/orders/${orderId}`, { method: 'PUT', body: payload })
}

// ---------- Chat ----------

export function listMessages(opts: { beforeMessageId?: number; pageSize?: number } = {}) {
  const q = new URLSearchParams({ page: '1', page_size: String(opts.pageSize ?? 50) })
  if (opts.beforeMessageId) q.set('before_message_id', String(opts.beforeMessageId))
  return apiRequest<Paginated<ChatMessage>>(`/messages?${q}`)
}

export function sendMessage(text: string) {
  return apiRequest<{ item: ChatMessage }>('/messages', {
    method: 'POST',
    body: { message_type: 'message', message_text: text, attachments: [], mentioned_user_ids: [] },
  })
}

export function editMessage(messageId: number, text: string) {
  return apiRequest<{ item: ChatMessage }>(`/messages/${messageId}`, {
    method: 'PUT',
    body: { message_text: text },
  })
}

export function deleteMessage(messageId: number) {
  return apiRequest<void>(`/messages/${messageId}`, { method: 'DELETE' })
}

// ---------- Inventories ----------

export function listInventories(opts: { page?: number; pageSize?: number } = {}) {
  const q = new URLSearchParams({ page: String(opts.page ?? 1), page_size: String(opts.pageSize ?? 30) })
  return apiRequest<Paginated<Inventory>>(`/inventories?${q}`)
}
export function getInventory(id: number) {
  return apiRequest<{ item: Inventory }>(`/inventories/${id}`)
}
export function createInventory(payload: unknown) {
  return apiRequest<{ item: Inventory }>('/inventories', { method: 'POST', body: payload })
}
export function updateInventory(id: number, payload: unknown) {
  return apiRequest<{ item: Inventory }>(`/inventories/${id}`, { method: 'PUT', body: payload })
}
export function updateInventoryStatus(id: number, statusId: number) {
  return apiRequest<{ item: Inventory }>(`/inventories/${id}/status`, {
    method: 'PUT',
    body: { inventory_status_id: statusId },
  })
}

// ---------- Product registrations (приёмки) ----------

export function listRegistrations(opts: { page?: number; pageSize?: number } = {}) {
  const q = new URLSearchParams({ page: String(opts.page ?? 1), page_size: String(opts.pageSize ?? 30) })
  return apiRequest<Paginated<ProductRegistration>>(`/product-registrations?${q}`)
}
export function getRegistration(id: number) {
  return apiRequest<{ item: ProductRegistration }>(`/product-registrations/${id}`)
}
export function createRegistration(payload: unknown) {
  return apiRequest<{ item: ProductRegistration }>('/product-registrations', { method: 'POST', body: payload })
}
export function updateRegistration(id: number, payload: unknown) {
  return apiRequest<{ item: ProductRegistration }>(`/product-registrations/${id}`, { method: 'PUT', body: payload })
}
export function updateRegistrationStatus(id: number, statusId: number) {
  return apiRequest<{ item: ProductRegistration }>(`/product-registrations/${id}/status`, {
    method: 'PUT',
    body: { product_registration_status_id: statusId },
  })
}

// ---------- Users ----------

export function listUsers(opts: { search?: string; page?: number; pageSize?: number } = {}) {
  const q = new URLSearchParams({
    page: String(opts.page ?? 1),
    page_size: String(opts.pageSize ?? 100),
  })
  if (opts.search) q.set('search', opts.search)
  return apiRequest<Paginated<User>>(`/users?${q}`)
}

export function updateUser(
  userId: number,
  patch: Partial<Pick<User, 'user_active' | 'user_admin'>>,
) {
  return apiRequest<{ item: User }>(`/users/${userId}`, { method: 'PUT', body: patch })
}

// ---------- Audit ----------

export function listAuditEvents(
  opts: { entityType?: string; eventType?: string; page?: number; pageSize?: number } = {},
) {
  const q = new URLSearchParams({
    page: String(opts.page ?? 1),
    page_size: String(opts.pageSize ?? 50),
  })
  if (opts.entityType) q.set('entity_type', opts.entityType)
  if (opts.eventType) q.set('event_type', opts.eventType)
  return apiRequest<Paginated<AuditEvent>>(`/audit-events?${q}`)
}
