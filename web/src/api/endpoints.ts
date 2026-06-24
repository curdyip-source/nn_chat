import { apiRequest } from './client'
import type {
  AuditEvent,
  AuthResponse,
  Contact,
  Currency,
  Establishment,
  Order,
  OrderCreate,
  OrderMethod,
  OrderUpdate,
  Paginated,
  Product,
  ProductImportJob,
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

// ---------- Orders ----------

export function listOrders(
  opts: { page?: number; pageSize?: number; statusId?: number | null; search?: string } = {},
) {
  const q = new URLSearchParams({
    page: String(opts.page ?? 1),
    page_size: String(opts.pageSize ?? 30),
  })
  if (opts.statusId != null) q.set('status_id', String(opts.statusId))
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
