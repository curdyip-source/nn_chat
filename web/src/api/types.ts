// Типы API. Имена полей повторяют сериализаторы бэкенда (snake_case).

export type User = {
  user_id: number
  user_login: string
  user_first_name?: string | null
  user_second_name?: string | null
  user_admin: boolean
  user_active?: boolean
}

export type AuthResponse = {
  access_token?: string
  token?: string
  refresh_token?: string
  user: User
}

export type SetupStatus = {
  bootstrap_required: boolean
  users_count: number
}

export type Status = {
  status_id: number
  status_type: string
  status_status: string
  status_color: string | null
}

export type Establishment = {
  establishment_id: number
  establishment_name: string
}

export type OrderMethod = {
  order_method_id: number
  order_method_name: string
  order_method_sub_methods: string[]
}

export type Currency = {
  currency_id: number
  currency_name: string
  currency_sign: string | null
}

export type ReferenceData = {
  establishments: Establishment[]
  order_methods: OrderMethod[]
  statuses: Status[]
  currencies: Currency[]
}

export type Product = {
  product_id: number
  product_article: string
  product_name: string
  product_cost_usd: string
}

export type ProductImportJob = {
  job_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  filename: string | null
  created: number
  updated: number
  skipped: number
  processed: number
  total_rows: number
  total_products: number
  error_message: string | null
}

export type Contact = {
  contact_id: number
  contact_name: string
  contact_type: 'buyer' | 'supplier'
  contact_info?: string | null
  contact_establishment_id?: number | null
  contact_order_method_id?: number | null
  contact_order_sub_method?: string | null
}

// ----- Создание заказа -----

export type OrderItemCreate = {
  product_id?: number | null
  product_article?: string | null
  product_name?: string | null
  order_item_quantity: number
  order_item_price: string
  order_item_status_id?: number | null
  order_item_currency_id?: number | null
}

export type OrderCreate = {
  order_establishment_id: number
  order_method_id: number
  order_sub_method?: string | null
  order_contact_method?: string | null
  order_customer: string
  order_info: string
  save_contact: boolean
  order_status_id?: number | null
  items: OrderItemCreate[]
}

export type OrderItem = {
  order_item_id: number
  order_item_product_id?: number | null
  order_item_name: string
  order_item_article: string | null
  order_item_quantity: number
  order_item_price: string
  order_item_status_id?: number | null
  order_item_status?: string | null
  order_item_status_color?: string | null
  order_item_supplier?: string | null
  order_item_note?: string | null
  order_item_currency_id?: number | null
}

export type Order = {
  order_id: number
  order_establishment_id?: number | null
  order_establishment_name?: string | null
  order_method_id?: number | null
  order_method_name?: string | null
  order_sub_method?: string | null
  order_contact_method?: string | null
  order_customer: string
  order_info: string
  order_status_id?: number | null
  order_status?: string | null
  order_status_color?: string | null
  order_owner_user_login?: string | null
  order_created_at?: string | null
  items: OrderItem[]
}

export type OrderUpdateItem = {
  product_id?: number | null
  product_article?: string | null
  product_name?: string | null
  order_item_quantity: number
  order_item_price: string
  order_item_status_id?: number | null
  order_item_currency_id?: number | null
  order_item_supplier?: string | null
  order_item_note?: string | null
}

export type OrderUpdate = {
  order_establishment_id: number
  order_method_id: number
  order_sub_method?: string | null
  order_contact_method?: string | null
  order_customer: string
  order_info: string
  order_status_id: number
  items: OrderUpdateItem[]
}

export type AuditEvent = {
  audit_event_id: number
  actor_user_id: number | null
  actor_user_login: string | null
  entity_type: string
  entity_id: number | null
  event_type: string
  event_payload: Record<string, unknown> | null
  created_at: string | null
}

export type Paginated<T> = {
  items: T[]
  pagination?: { page: number; page_size: number; total: number }
}
