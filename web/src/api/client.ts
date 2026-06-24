// Тонкий клиент над fetch: базовый путь /api/v1, Bearer-токен, единая обработка ошибок.
// Контракт сохранён из legacy-админки (ключи хранения, /auth/login, проверка user_admin).

const API_BASE = '/api/v1'
export const TOKEN_KEY = 'admin.accessToken'
export const USER_KEY = 'admin.user'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** Бросается при 401 — токен невалиден/истёк, нужно разлогинить. */
export class UnauthorizedError extends ApiError {
  constructor(message = 'Сессия истекла') {
    super(401, message)
    this.name = 'UnauthorizedError'
  }
}

let accessToken: string = localStorage.getItem(TOKEN_KEY) ?? ''
let onUnauthorized: (() => void) | null = null

export function setAccessToken(token: string) {
  accessToken = token
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function getAccessToken(): string {
  return accessToken
}

/** Колбэк, который вызовется на любой 401 (обычно — переход на экран логина). */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

type RequestOptions = {
  method?: string
  body?: unknown
  /** FormData отправляется как есть (для загрузки файлов). */
  raw?: boolean
  signal?: AbortSignal
  /** Не дёргать onUnauthorized на 401 (например, для самого логина). */
  silent401?: boolean
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json()
    return (
      data?.error?.message ??
      data?.detail ??
      data?.message ??
      `Ошибка ${response.status}`
    )
  } catch {
    return `Ошибка ${response.status}`
  }
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, raw = false, signal, silent401 = false } = options

  const headers: Record<string, string> = {}
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  let payload: BodyInit | undefined
  if (body instanceof FormData) {
    payload = body
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  void raw

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: payload,
    signal,
  })

  if (response.status === 401) {
    if (!silent401 && onUnauthorized) onUnauthorized()
    throw new UnauthorizedError(await parseError(response))
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response))
  }

  if (response.status === 204) return undefined as T
  const text = await response.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}
