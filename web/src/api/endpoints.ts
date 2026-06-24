import { apiRequest } from './client'
import type {
  AuthResponse,
  Contact,
  Order,
  OrderCreate,
  Paginated,
  Product,
  ReferenceData,
  SetupStatus,
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

// ---------- Products ----------

export function searchProducts(search: string, signal?: AbortSignal) {
  const q = new URLSearchParams({ search, page: '1', page_size: '20' })
  return apiRequest<Paginated<Product>>(`/products?${q}`, { signal })
}

export function createProduct(input: {
  product_article: string
  product_name: string
  product_cost_usd: string
}) {
  return apiRequest<{ item: Product }>('/products', { method: 'POST', body: input })
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

export function listOrders(page = 1, pageSize = 20) {
  const q = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  return apiRequest<Paginated<Order>>(`/orders?${q}`)
}

export function createOrder(payload: OrderCreate) {
  return apiRequest<{ item: Order }>('/orders', { method: 'POST', body: payload })
}
