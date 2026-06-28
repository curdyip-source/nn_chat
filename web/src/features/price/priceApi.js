// Тонкая обёртка над fetch для прайс-секции.
//
// Прайс живёт отдельным бэкендом (контейнер nn_vla), его API проксируется nginx'ом
// чата под префиксом /price-api. Здесь же подмешиваем Bearer-токен чата: единый вход —
// прайс доверяет тому же AUTH_TOKEN_SECRET и валидирует токен сам (см. бэкенд nn_vla).
//
// Вьюхи прайса написаны под нативный fetch (читают r.ok / r.json()), поэтому priceFetch
// сохраняет сигнатуру fetch: меняется только префикс пути и заголовок авторизации.
import { getAccessToken, refreshAccessToken } from '../../api/client'

const PRICE_BASE = '/price-api'

function withAuth(init = {}) {
  const headers = new Headers(init.headers || {})
  const token = getAccessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return { ...init, headers }
}

/**
 * fetch к API прайса. `path` — как в исходных вьюхах ("/api/..."), префикс /price-api
 * добавляется здесь. На 401 один раз пробуем обновить access-токен чата и повторяем.
 */
export async function priceFetch(path, init = {}) {
  const url = `${PRICE_BASE}${path}`
  let response = await fetch(url, withAuth(init))
  if (response.status === 401 && (await refreshAccessToken())) {
    response = await fetch(url, withAuth(init))
  }
  return response
}
