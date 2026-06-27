// Тонкий клиент над fetch: базовый путь /api/v1, Bearer-токен, единая обработка ошибок.
// Контракт сохранён из legacy-админки (ключи хранения, /auth/login, проверка user_admin).

const API_BASE = '/api/v1'
export const TOKEN_KEY = 'admin.accessToken'
export const REFRESH_KEY = 'admin.refreshToken'
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
let refreshToken: string = localStorage.getItem(REFRESH_KEY) ?? ''
let onUnauthorized: (() => void) | null = null

export function setAccessToken(token: string) {
  accessToken = token
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function getAccessToken(): string {
  return accessToken
}

export function setRefreshToken(token: string) {
  refreshToken = token
  if (token) localStorage.setItem(REFRESH_KEY, token)
  else localStorage.removeItem(REFRESH_KEY)
}

let refreshInFlight: Promise<boolean> | null = null

/**
 * Exchange the refresh token for a fresh access token (and rotated refresh token).
 * Concurrent callers share one in-flight request so a token rotation isn't raced.
 * Returns true on success. Keeps the web session (and its SSE stream) alive past the
 * 30-minute access-token TTL instead of logging the user out.
 */
export async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
        if (!response.ok) return false
        const data = await response.json()
        const newAccess = data?.access_token ?? data?.token ?? ''
        if (!newAccess) return false
        setAccessToken(newAccess)
        if (data?.refresh_token) setRefreshToken(data.refresh_token)
        return true
      } catch {
        return false
      } finally {
        refreshInFlight = null
      }
    })()
  }
  return refreshInFlight
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
  /** Внутреннее: запрос уже повторялся после обновления токена. */
  _retried?: boolean
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
  const { method = 'GET', body, raw = false, signal, silent401 = false, _retried = false } = options

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
    // Access token likely expired — refresh once and retry before giving up.
    if (!silent401 && !_retried && (await refreshAccessToken())) {
      return apiRequest<T>(path, { ...options, _retried: true })
    }
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

/**
 * Consume the SSE realtime stream (/messages/stream) via fetch — needed because the native
 * EventSource can't send the Authorization header. Calls `onEvent` for each parsed event and
 * resolves when the stream closes. Throws UnauthorizedError on 401 so callers can stop retrying.
 */
export async function streamEvents(
  onEvent: (event: unknown) => void,
  signal: AbortSignal,
): Promise<void> {
  const headers: Record<string, string> = { Accept: 'text/event-stream' }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  const response = await fetch(`${API_BASE}/messages/stream`, { headers, signal })
  if (response.status === 401) throw new UnauthorizedError(await parseError(response))
  if (!response.ok || !response.body) throw new ApiError(response.status, `Ошибка ${response.status}`)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let boundary: number
    while ((boundary = buffer.indexOf('\n\n')) >= 0) {
      const rawEvent = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const data = rawEvent
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice('data:'.length).trim())
        .join('')
      if (!data) continue // heartbeat/comment
      try {
        onEvent(JSON.parse(data))
      } catch {
        // ignore malformed event
      }
    }
  }
}
